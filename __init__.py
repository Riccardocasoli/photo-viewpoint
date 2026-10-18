def classFactory(iface):
    from .plugin import PhotoPlugin
    return PhotoPlugin(iface)
