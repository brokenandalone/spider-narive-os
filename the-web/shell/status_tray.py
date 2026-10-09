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
