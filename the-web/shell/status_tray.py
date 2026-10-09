"""Read-only StatusNotifier watcher client for background app list.

Uses existing KDE-compatible watcher if available. Never steals watcher name,
spawns another Plasma shell or executes application supplied commands.
"""
import asyncio

async def status_items():
    try:
        from dbus_next.aio import MessageBus
        from dbus_next import BusType
        bus=await MessageBus(bus_type=BusType.SESSION).connect()
        try:
            obj=await bus.introspect('org.kde.StatusNotifierWatcher','/StatusNotifierWatcher')
            proxy=bus.get_proxy_object('org.kde.StatusNotifierWatcher','/StatusNotifierWatcher',obj)
            properties=proxy.get_interface('org.freedesktop.DBus.Properties')
            items=await asyncio.wait_for(properties.call_get('org.kde.StatusNotifierWatcher','RegisteredStatusNotifierItems'),timeout=2)
            return sorted(str(s)[:256] for s in items.value if isinstance(s,str))[:50]
        finally:
            bus.disconnect()
    except (ImportError,Exception):
        return []

def get_status_items():
    return asyncio.run(status_items())

def split_item(value):
    if not isinstance(value,str) or not value or len(value)>256:
        raise ValueError('Invalid tray item')
    if value.startswith('/'): raise ValueError('Missing service')
    if '/' in value:
        name,path=value.split('/',1)
        path='/'+path
    else:
        name,path=value,'/StatusNotifierItem'
    if not name or not path.startswith('/') or '..' in path:
        raise ValueError('Invalid notifier identity')
    return name,path

async def activate(value):
    from dbus_next.aio import MessageBus
    from dbus_next import BusType
    service,path=split_item(value)
    bus=await MessageBus(bus_type=BusType.SESSION).connect()
    try:
        tree=await asyncio.wait_for(bus.introspect(service,path),timeout=2)
        obj=bus.get_proxy_object(service,path,tree)
        iface=obj.get_interface('org.kde.StatusNotifierItem')
        await asyncio.wait_for(iface.call_activate(0,0),timeout=2)
    finally:
        bus.disconnect()

def activate_item(value):
    asyncio.run(activate(value))

async def item_details(value):
    """Read common StatusNotifier properties without invoking app actions."""
    from dbus_next.aio import MessageBus
    from dbus_next import BusType
    service,path=split_item(value)
    bus=await MessageBus(bus_type=BusType.SESSION).connect()
    try:
        tree=await asyncio.wait_for(bus.introspect(service,path),timeout=2)
        obj=bus.get_proxy_object(service,path,tree)
        props=obj.get_interface('org.freedesktop.DBus.Properties')
        details={'id':value,'service':service,'title':service,'status':'Unknown',
                 'icon_name':'','menu':False,'item_is_menu':False}
        for key in ('Title','Status','IconName','Menu','ItemIsMenu'):
            try:
                variant=await asyncio.wait_for(
                    props.call_get('org.kde.StatusNotifierItem',key),timeout=2)
                data=variant.value
                if key=='Title' and isinstance(data,str): details['title']=data[:120]
                if key=='Status' and isinstance(data,str): details['status']=data[:30]
                if key=='IconName' and isinstance(data,str): details['icon_name']=data[:120]
                if key=='Menu' and isinstance(data,str): details['menu']=data.startswith('/')
                if key=='ItemIsMenu' and isinstance(data,bool): details['item_is_menu']=data
            except Exception:
                continue
        return details
    finally:
        bus.disconnect()

def get_item_details(value):
    return asyncio.run(item_details(value))

async def secondary_activate(value):
    """Request the app's native secondary action if it supports the protocol."""
    from dbus_next.aio import MessageBus
    from dbus_next import BusType
    service,path=split_item(value)
    bus=await MessageBus(bus_type=BusType.SESSION).connect()
    try:
        tree=await asyncio.wait_for(bus.introspect(service,path),timeout=2)
        obj=bus.get_proxy_object(service,path,tree)
        iface=obj.get_interface('org.kde.StatusNotifierItem')
        await asyncio.wait_for(iface.call_secondary_activate(0,0),timeout=2)
    finally:
        bus.disconnect()

def secondary_activate_item(value):
    asyncio.run(secondary_activate(value))
