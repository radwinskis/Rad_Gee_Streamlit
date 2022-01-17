import streamlit as st
import geemap.foliumap as geemap
import ee
#import os
from datetime import date
import datetime

#os.environ["EARTHENGINE_TOKEN"] == st.secrets["EARTHENGINE_TOKEN"]
#If app is a contained app, wrap the app in a function called app():

st.set_page_config(layout="wide")
st.title("Testing My GEE Rad App Interface")


ee.Initialize()

### Functions ###
def image_dater(image):
    date = ee.Number(image.date().format('YYYY-MM-dd'))
    return image.set({'Date_Filter': date})

def image_grab(img_col, img_selector):
    new_col = img_col.filter(ee.Filter.eq('Date_Filter', img_selector)) #.filter(ee.Filter.eq('Date_Filter', img_selector))
    new_col_list = new_col.toList(new_col.size())
    return ee.Image(new_col_list.get(0))

def image_grab2(img_col, img_selector):
    new_col = img_col.filter(ee.Filter.eq('Date_Filter', img_selector)) #.filter(ee.Filter.eq('Date_Filter', img_selector))
    new_col_list = new_col.toList(new_col.size())
    return ee.Image(new_col_list.get(0))

def maskL8clouds(image):
    cloudBitMask = ee.Number(2).pow(3).int()
    CirrusBitMask = ee.Number(2).pow(2).int()
    qa = image.select('QA_PIXEL')
    cloud_mask = qa.bitwiseAnd(cloudBitMask).eq(0)
    cirrus_mask = qa.bitwiseAnd(CirrusBitMask).eq(0)
    return image.updateMask(cloud_mask).updateMask(cirrus_mask)

def temperature_bands(img):
    date = ee.Number(img.date().format('YYYY-MM-dd'))
    scale1 = ['ST_ATRAN', 'ST_EMIS']
    scale2 = ['ST_DRAD', 'ST_TRAD', 'ST_URAD']
    scale1_names = ['transmittance', 'emissivity']
    scale2_names = ['downwelling', 'B10_radiance', 'upwelling']
    scale1_bands = img.select(scale1).multiply(0.0001).rename(scale1_names) #Scaled to new L8 collection
    scale2_bands = img.select(scale2).multiply(0.001).rename(scale2_names) #Scaled to new L8 collection
    return scale1_bands.addBands(scale2_bands)
def landsat_LST(image):
    #date = ee.Number(image.date().format('YYYY-MM-dd'))
    k1 = 774.89
    k2 = 1321.08
    LST = image.expression(
        '(k2/log((k1/((B10_rad - upwelling - transmittance*(1 - emissivity)*downwelling)/(transmittance*emissivity)))+1)) - 273.15',
        {'k1': k1,
        'k2': k2,
        'B10_rad': image.select('B10_radiance'),
        'upwelling': image.select('upwelling'),
        'transmittance': image.select('transmittance'),
        'emissivity': image.select('emissivity'),
        'downwelling': image.select('downwelling')})
    return LST.rename('LST') #.set({'Date_Filter': date}) #Outputs temperature in C



### Application Body ###
st.write('Choose your initial parameters. Note: setting a large date difference/collection will cause slower load times')
st.write('To refresh settings to default, refresh the page using your browser')
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
with col1:
    cloud_options = st.radio('Cloud Masking?', ['Yes', 'No'], 0, key='clouds')
with col2:
    dataset_options = st.selectbox('Dataset Selection', ['Landsat 8 True Color', \
        'Landsat 8 Surface Temperature', 'Landsat 8 Vegetation False Color'], 0, key='dataset')
with col3:
    yr_ago = datetime.datetime.now() - datetime.timedelta(days=365)
    start_date = st.date_input('Collection Start Date (optional)', yr_ago)
with col4:
    end_date = st.date_input('Collection End Date (optional)', datetime.datetime.now())
#st.write(cloud_options)
#st.write(str(end_date))

locations = ['Salt Lake Valley', 'Bonneville Basin', 'Delta - St George', 'Moab area', \
    'Price - Capitol Reef - Grand Staircase', 'Uintas - Price']
#st.write('Choose region of Utah')
location = st.selectbox('Location', locations, 0, key='location')
if location=='Salt Lake Valley':
    lat = 40.7514
    long = -111.9064
    path = 38
    row_N = 31
    row_S = 32
elif location=='Bonneville Basin':
    lat = 40.9353
    long = -113.4461
    path = 39
    row_N = 31
    row_S = 32
elif location=='Delta - St George':
    lat = 38.6705
    long = -112.3404
    path = 38
    row_N = 33
    row_S = 34
elif location=='Moab area':
    lat = 38.5726
    long = -109.5508
    path = 36
    row_N = 33
    row_S = 34
elif location=='Price - Capitol Reef - Grand Staircase':
    lat = 38.0740
    long = -111.1142
    path = 37
    row_N = 33
    row_S = 34
elif location=='Uintas - Price':
    lat = 40.7306
    long = -110.5163
    path = 37
    row_N = 31
    row_S = 32



if cloud_options=='Yes':
    landsat_N = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterDate(ee.Date(str(start_date)).format('YYYY-MM-dd'), ee.Date(str(end_date)).format('YYYY-MM-dd')) \
    .filter(ee.Filter.And(ee.Filter.eq('WRS_PATH', path), ee.Filter.eq('WRS_ROW', row_N))).map(image_dater).map(maskL8clouds)

    landsat_S = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterDate(ee.Date(str(start_date)).format('YYYY-MM-dd'), ee.Date(str(end_date)).format('YYYY-MM-dd')) \
    .filter(ee.Filter.And(ee.Filter.eq('WRS_PATH', path), ee.Filter.eq('WRS_ROW', row_S))).map(image_dater).map(maskL8clouds)
else:
    landsat_N = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterDate(ee.Date(str(start_date)).format('YYYY-MM-dd'), ee.Date(str(end_date)).format('YYYY-MM-dd')) \
    .filter(ee.Filter.And(ee.Filter.eq('WRS_PATH', path), ee.Filter.eq('WRS_ROW', row_N))).map(image_dater)

    landsat_S = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterDate(ee.Date(str(start_date)).format('YYYY-MM-dd'), ee.Date(str(end_date)).format('YYYY-MM-dd')) \
    .filter(ee.Filter.And(ee.Filter.eq('WRS_PATH', path), ee.Filter.eq('WRS_ROW', row_S))).map(image_dater)

ls_dates = landsat_N.aggregate_array('Date_Filter').getInfo() #List of dates
ls_date_value = ee.Date(landsat_N.aggregate_array('Date_Filter').getInfo()[-1]).format('YYYY-MM-dd') #Most recent date

ls_dates2 = landsat_S.aggregate_array('Date_Filter').getInfo() #List of dates
ls_date_value2 = ee.Date(landsat_S.aggregate_array('Date_Filter').getInfo()[-1]).format('YYYY-MM-dd') #Most recent date

N_scaled_bands = landsat_N.map(temperature_bands)
S_scaled_bands = landsat_S.map(temperature_bands)
N_scaled_col = landsat_N.combine(N_scaled_bands)
S_scaled_col = landsat_S.combine(N_scaled_bands)
N_LST_col = N_scaled_bands.map(landsat_LST)
S_LST_col = S_scaled_bands.map(landsat_LST)
N_LST = landsat_N.combine(N_LST_col).map(image_dater)
S_LST = landsat_S.combine(S_LST_col).map(image_dater)
#st.write(N_LST.first().getInfo().get('properties').get('Date_Filter'))
#st.write(landsat_N.first().getInfo().get('properties').get('Date_Filter'))
#st.write(landsat_N.getInfo())


st.write("Choose dates of each north and south image of the swath (this is because they don't always match by default)")
col5, col6 = st.columns([2, 2])
with col5:
    N_img_date = st.selectbox('North Image Date', ls_dates, len(ls_dates)-1, key="N_img_date")
with col6:
    S_img_date = st.selectbox('South Image Date', ls_dates2, len(ls_dates2)-1, key="S_img_date")

if dataset_options=='Landsat 8 True Color':
    col7, col8 = st.columns([2, 2])
    with col7:
        min = st.slider('Minimum Display Value', min_value=0, max_value=600, value=0, key='min_stretch_value')
    with col8:
        max = st.slider('Maximum Display Value (raise for displaying bright objects)', min_value=10000, max_value=60000, value=24000, key='max_stretch_value')    
    Map = geemap.Map(center=(lat, long), zoom=10)
    ls_true_vis = {'bands': ['SR_B4', 'SR_B3', 'SR_B2'], 'min': min, 'max': max, 'gamma': [0.6, 0.6, 0.6]}
    Map.addLayer(image_grab(landsat_N, N_img_date), ls_true_vis, 'northern swath image')
    Map.addLayer(image_grab(landsat_S, S_img_date), ls_true_vis, 'southern swath image')
    Map.to_streamlit(height=800)
elif dataset_options=='Landsat 8 Surface Temperature':
    col7, col8 = st.columns([2, 2])
    with col7:
        min = st.slider('Minimum Display Temperature (C)', min_value=-30, max_value=8, value=-18, key='min_temp')
    with col8:
        max = st.slider('Maximum Display Temperature (C)', min_value=9, max_value=48, value=38, key='max_temp')
    Map = geemap.Map(center=(lat, long), zoom=10)
    jet = ['#00007F', '#002AFF', '#00D4FF', '#7FFF7F', '#FFD400', '#FF2A00', '#7F0000']
    inferno = ['#000004', '#320A5A', '#781B6C', '#BB3654', '#EC6824', '#FBB41A', '#FCFFA4']
    thermal = ['042333', '2c3395', '744992', 'b15f82', 'eb7958', 'fbb43d', 'e8fa5b']
    thermal_vis = {'bands': ['LST'], 'min':min, 'max':max, 'palette':thermal}
    Map.addLayer(image_grab(N_LST, N_img_date), thermal_vis, 'northern swath image')
    Map.addLayer(image_grab(S_LST, S_img_date), thermal_vis, 'southern swath image')
    Map.add_colorbar(colors=thermal, vmin=min, vmax=max, caption = "Surface Temperature (C)", layer_name = 'Surface Temperature')
    #Map.addLayer(N_LST.first(), thermal_vis, 'northern swath image')
    Map.to_streamlit(height=800)
elif dataset_options=='Landsat 8 Vegetation False Color':
    col7, col8 = st.columns([2, 2])
    with col7:
        min = st.slider('Minimum Display Value', min_value=0, max_value=600, value=0, key='min_stretch_value')
    with col8:
        max = st.slider('Maximum Display Value (raise for displaying bright objects)', min_value=10000, max_value=60000, value=24000, key='max_stretch_value')    
    Map = geemap.Map(center=(lat, long), zoom=10)
    ls_true_vis = {'bands': ['SR_B5', 'SR_B4', 'SR_B3'], 'min': min, 'max': max, 'gamma': [0.6, 0.6, 0.6]}
    Map.addLayer(image_grab(landsat_N, N_img_date), ls_true_vis, 'northern swath image')
    Map.addLayer(image_grab(landsat_S, S_img_date), ls_true_vis, 'southern swath image')
    Map.to_streamlit(height=800)