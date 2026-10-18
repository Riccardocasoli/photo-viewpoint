"""English field schema and non-destructive compatibility with pre-0.6 layers."""
LEGACY={'code':'codice','caption':'Didascalia'}


def field_name(owner,name):
    if not hasattr(owner,'fields'):
        return LEGACY.get(name) if LEGACY.get(name) in owner and name not in owner else name
    fields=owner.fields()
    if fields.indexFromName(name)>=0:return name
    legacy=LEGACY.get(name)
    return legacy if legacy and fields.indexFromName(legacy)>=0 else name


def caption_length(driver=''):
    return 254 if driver=='ESRI Shapefile' else 2000


def preferred_names(names):
    first=[n for n in ('code','codice','caption','Didascalia','distGPS') if n in names]
    return first+[n for n in names if n not in first]


def configure_table(layer):
    for key,label in [('code','Code'),('caption','Caption'),('distGPS','distGPS')]:
        idx=layer.fields().indexFromName(field_name(layer,key))
        if idx>=0:layer.setFieldAlias(idx,label)
    config=layer.attributeTableConfig()
    config.update(layer.fields())
    columns=config.columns()
    names=[c.name for c in columns]
    rank={n:i for i,n in enumerate(preferred_names(names))}
    columns.sort(key=lambda c:rank.get(c.name,len(rank)))
    config.setColumns(columns)
    layer.setAttributeTableConfig(config)
