"""Optional freedesktop DBus desktop bridge for The Web.

Own org.freedesktop.Notifications only if no other provider owns it.
Watch StatusNotifierItem registrations via org.kde.StatusNotifierWatcher when
available. Never replace an existing daemon, and never execute notification
payloads. Requires optional python3-dbus-next.
"""
import asyncio
from collections import OrderedDict
from datetime import datetime
import json
from pathlib import Path
import os

MAX_ITEMS=100

def clean(value,limit):
    return str(value).replace('\x00','')[:limit]

def append_history(path,title,message,app):
    # JSON-lines spool, readable only by the logged-in user.
    path=Path(path)
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if path.is_symlink(): raise OSError('Refusing symlinked notification journal')
    old=[]
    try:
        if path.exists() and path.stat().st_size<=131072:
            old=[line for line in path.read_text().splitlines()[-MAX_ITEMS:] if line]
    except (OSError,UnicodeError):
        pass
    entry=json.dumps({'title':clean(title,80),'message':clean(message,300),
                      'app':clean(app,80),'time':datetime.now().isoformat(timespec='seconds')})
    import tempfile
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.tray-journal-')
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            stream.write('\n'.join((old+[entry])[-MAX_ITEMS:])+'\n')
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

class NotificationModel:
    def __init__(self,path):
        self.path=Path(path)
        self.serial=0
    def notify(self,app_name,summary,body):
        self.serial=(self.serial%2147483646)+1
        append_history(self.path,summary,body,app_name)
        return self.serial

async def serve(path):
    from dbus_next.aio import MessageBus
    from dbus_next.service import ServiceInterface, method, signal
    from dbus_next import BusType, RequestNameReply, Variant
    model=NotificationModel(path)
    class Notifications(ServiceInterface):
        def __init__(self):super().__init__('org.freedesktop.Notifications')
        @method()
        def GetCapabilities(self)->'as':return ['body','persistence']
        @method()
        def GetServerInformation(self)->'ssss':return ['The Web','Spider OS','1.0','1.2']
        @method()
        def Notify(self,app_name:'s',replaces_id:'u',app_icon:'s',
                   summary:'s',body:'s',actions:'as',hints:'a{sv}',expire_timeout:'i')->'u':
            return model.notify(app_name,summary,body)
        @method()
        def CloseNotification(self,id:'u'):
            self.NotificationClosed(id,3)
        @signal()
        def NotificationClosed(self,id:'u',reason:'u')->'uu':return [id,reason]
        @signal()
        def ActionInvoked(self,id:'u',action_key:'s')->'us':return [id,action_key]
    bus=await MessageBus(bus_type=BusType.SESSION).connect()
    reply=await bus.request_name('org.freedesktop.Notifications',flags=0)
    if reply not in (RequestNameReply.PRIMARY_OWNER,RequestNameReply.ALREADY_OWNER):
        print('Existing notifications provider retained; The Web bridge not taking over.')
        bus.disconnect()
        return 0
    bus.export('/org/freedesktop/Notifications',Notifications())
    print('The Web notifications bridge started.')
    await bus.wait_for_disconnect()
    return 0

def main():
    try:
        import dbus_next
    except ImportError:
        print('Optional python3-dbus-next unavailable; leaving other services untouched.')
        return 0
    home=Path.home()
    return asyncio.run(serve(home/'.local/state/spider-os/external-notifications.jsonl'))

if __name__=='__main__':
    raise SystemExit(main())
