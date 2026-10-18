"""Create a separate dataset; never rename or delete fields in a live legacy layer."""
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsVectorLayer,QgsField,QgsFeature
from .schema import field_name,preferred_names
from .create_layer_dialog import write_dataset
from .photo_metadata import configure_tracking


def make_english_copy(source,path):
    names=[f.name() for f in source.fields()]
    output_names=[]
    for name in names:
        target={'codice':'code','Didascalia':'caption'}.get(name,name)
        if target not in output_names:output_names.append(target)
    for name in ('caption','distGPS'):
        if name not in output_names:output_names.append(name)
    output_names=preferred_names(output_names)
    memory=QgsVectorLayer('Point',source.name()+' — English','memory');memory.setCrs(source.crs())
    fields=[]
    for name in output_names:
        old=source.fields().indexFromName(field_name(source,name))
        if name=='caption':field=QgsField(name,QVariant.String,len=2000)
        elif old>=0:field=QgsField(source.fields().field(old));field.setName(name)
        else:field=QgsField(name,QVariant.Double,len=24,prec=3)
        fields.append(field)
    if not memory.dataProvider().addAttributes(fields):raise ValueError('Cannot create English schema.')
    memory.updateFields()
    batch=[]
    for feature in source.getFeatures():
        new=QgsFeature(memory.fields());new.setGeometry(feature.geometry())
        for name in output_names:
            old=source.fields().indexFromName(field_name(source,name))
            if old>=0:new[name]=feature[old]
        batch.append(new)
        if len(batch)>=500:
            if not memory.dataProvider().addFeatures(batch)[0]:raise ValueError('Cannot copy records.')
            batch=[]
    if batch and not memory.dataProvider().addFeatures(batch)[0]:raise ValueError('Cannot copy records.')
    result=write_dataset(memory,memory.name(),'GPKG',path)
    configure_tracking(result)
    return result
