import streamlit as st
import geemap.foliumap as geemap
import geemap as gm
# import geemap
import ee
#import os
from datetime import date
import datetime
from RadGEEToolbox_v1_0_1 import LandsatCollection, Sentinel2Collection
#os.environ["EARTHENGINE_TOKEN"] == st.secrets["EARTHENGINE_TOKEN"]
#If app is a contained app, wrap the app in a function called app():

st.set_page_config(layout="wide")
st.title("Utah Remote Sensing Interface | Satellite Imagery Explorer")
st.subheader('Choose from true color, vegetation false color, or land surface temperature datasets')
st.subheader('Code written with Google Earth Engine, geemap, Streamlit, and love | Made by Mark Radwin, PhD Candidate - University of Utah')

with st.expander("Instructions and information"):
    st.markdown('This web app is designed to be an easy to use interface to explore and \
        save select satellite imagery from the state of Utah. The data used for this application \
        is from Google Earth Engine but is acquired by NASA, USGS, and/or ESA. \
        To use the app, please define any initial dataset parameters such as cloud masking (removes pixels identified as clouds), \
        processed dataset selection (i.e. true color imagery vs land surface temperature), and the image collection start/end dates.\
        Then select the region of Utah in which you wish to image using the location dropdown. \
        Then, adjust the image date which you wish to display using the dropdown. To adjust the contrast of the scene, \
        you can change the minimum and maximum display value. Raising the max value will darken the scene and \
        lowering the max will lighten the scene. For Land Surface Temperature (LST), you may choose the actual min and max \
        temperatures (in C) displayed. After every change the page will load to enact your changes. The map will constantly update \
        your choices and has interactivity for panning and zooming. To save either the northern or southern image displayed as is, \
        click the buttons below the map to acquire a link which will open a new tab displaying the image of interest. To save the image \
        in this new tab, right-click the image and press Save Image As... The color palette used for LST is called thermal and is from https://github.com/gee-community/ee-palettes. \
        See my Github for more details on the code.')


gm.ee_initialize()

### Application Body ###
st.write('Choose your initial parameters. Note: setting a large date difference/collection will cause slower load times')
st.write('To refresh settings to default, refresh the page using your browser')
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
with col1:
    cloud_options = st.radio('Cloud Masking?', ['Yes', 'No'], 1, key='clouds')
with col2:
    dataset_options = st.selectbox('Dataset Selection', ['Landsat 8 & 9 True Color', 'Sentinel 2 True Color',\
        'Landsat 8 & 9 Surface Temperature', 'Landsat 8 & 9 Vegetation False Color'], 0, key='dataset')
with col3:
    yr_ago = datetime.datetime.now() - datetime.timedelta(days=31)
    start_date_input = st.date_input('Collection Start Date (optional)', yr_ago)
    start_date = ee.Date(str(start_date_input)).format('YYYY-MM-dd')
with col4:
    end_date_input = st.date_input('Collection End Date (optional)', datetime.datetime.now())
    end_date = ee.Date(str(end_date_input)).format('YYYY-MM-dd')
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
    tile_N = '12TVL'
    tile_S = '12TVK'
elif location=='Bonneville Basin':
    lat = 40.9353
    long = -113.4461
    path = 39
    row_N = 31
    row_S = 32
    tile_N = '12TTL'
    tile_S = '12TTK'
elif location=='Delta - St George':
    lat = 38.6705
    long = -112.3404
    path = 38
    row_N = 33
    row_S = 34
    tile_N = '12STH'
    tile_S = '12STG'
elif location=='Moab area':
    lat = 38.5726
    long = -109.5508
    path = 36
    row_N = 33
    row_S = 34
    tile_N = '12SXH'
    tile_S = '12SXG'
elif location=='Price - Capitol Reef - Grand Staircase':
    lat = 38.0740
    long = -111.1142
    path = 37
    row_N = 33
    row_S = 34
    tile_N = '12SVH'
    tile_S = '12SVG'
elif location=='Uintas - Price':
    lat = 40.7306
    long = -110.5163
    path = 37
    row_N = 31
    row_S = 32
    tile_N = '12TWL'
    tile_S = '12TWK'


if cloud_options=='Yes':
    landsat_N = LandsatCollection(start_date, end_date, row_N, path, 100).masked_clouds_collection
    landsat_S = LandsatCollection(start_date, end_date, row_S, path, 100).masked_clouds_collection
    landsat = landsat_N.CollectionStitch(landsat_S)

    sentinel_N = Sentinel2Collection(start_date, end_date, tile_N, 100, 30).masked_clouds_collection
    sentinel_S = Sentinel2Collection(start_date, end_date, tile_S, 100, 30).masked_clouds_collection
    sentinel = sentinel_N.CollectionStitch(sentinel_S)

else:
    landsat_N = LandsatCollection(start_date, end_date, row_N, path, 100)
    landsat_S = LandsatCollection(start_date, end_date, row_S, path, 100)
    landsat = landsat_N.CollectionStitch(landsat_S)

    sentinel_N = Sentinel2Collection(start_date, end_date, tile_N, 100, 30)
    sentinel_S = Sentinel2Collection(start_date, end_date, tile_S, 100, 30)
    sentinel = sentinel_N.CollectionStitch(sentinel_S)

ls_dates = sorted(landsat.dates_list)
ls_date_value = ee.Date(ls_dates[-1])

sn_dates = sorted(sentinel.dates_list)
ls_date_value = ee.Date(sn_dates[-1])
#Link for sn tile explorer https://eatlas.org.au/data/uuid/f7468d15-12be-4e3f-a246-b2882a324f59

LST = landsat.LST
#st.write(N_LST.first().getInfo().get('properties').get('Date_Filter'))
#st.write(landsat_N.first().getInfo().get('properties').get('Date_Filter'))
#st.write(landsat_N.getInfo())
# colw1, colw2, colw3 = st.columns([1, 1, 1])
# with colw2:
#     st.write("Choose date from collection to display")
#col5, col6 = st.columns([2, 2])
#if dataset_options=='Landsat 8 True Color':
if 'Landsat 8' in dataset_options:
    cold1, cold2, cold3 = st.columns([1, 1, 1])
    with cold2:
        img_date = st.selectbox('Choose image date to display', ls_dates, len(ls_dates)-1, key="Image_date_ls")
else:
    cold1, cold2, cold3 = st.columns([1, 1, 1])
    with cold2:
        img_date = st.selectbox('Choose image date to display', sn_dates, len(sn_dates)-1, key="Image_date_sn")

if dataset_options=='Landsat 8 & 9 True Color':
    col7, col8 = st.columns([2, 2])
    with col7:
        min = st.slider('Minimum Display Value', min_value=-500, max_value=5000, value=0, key='min_stretch_value')
    with col8:
        max = st.slider('Maximum Display Value (raise for displaying bright objects)', min_value=10000, max_value=60000, value=24000, key='max_stretch_value')  
    col9, col10, col11 = st.columns([1, 18, 1])
    with col10:  
        Map = geemap.Map(center=(lat, long), zoom=10)
        ls_true_vis = {'bands': ['SR_B4', 'SR_B3', 'SR_B2'], 'min': min, 'max': max, 'gamma': [0.6, 0.6, 0.6]}
        Map.addLayer(landsat.image_pick(img_date), ls_true_vis, 'Landsat imagery')
        Map.to_streamlit(height=800)
    url = landsat.image_pick(img_date).getThumbURL({'dimensions':2500, 'format':'png', 'bands':['SR_B4', 'SR_B3', 'SR_B2'], 'min': min, 'max': max, 'gamma': [0.6, 0.6, 0.6]})
    st.write('Image acquired by', landsat.image_pick(img_date).get('SPACECRAFT_ID').getInfo())
elif dataset_options=='Landsat 8 & 9 Surface Temperature':
    col7, col8 = st.columns([2, 2])
    with col7:
        min = st.slider('Minimum Display Temperature (C)', min_value=-30, max_value=8, value=0, key='min_temp')
    with col8:
        max = st.slider('Maximum Display Temperature (C)', min_value=9, max_value=65, value=50, key='max_temp')
    col9, col10, col11 = st.columns([1, 18, 1])
    with col10:
        Map = geemap.Map(center=(lat, long), zoom=10)
        jet = ['#00007F', '#002AFF', '#00D4FF', '#7FFF7F', '#FFD400', '#FF2A00', '#7F0000']
        inferno = ['#000004', '#320A5A', '#781B6C', '#BB3654', '#EC6824', '#FBB41A', '#FCFFA4']
        thermal = ['042333', '2c3395', '744992', 'b15f82', 'eb7958', 'fbb43d', 'e8fa5b']
        thermal_vis = {'bands': ['LST'], 'min':min, 'max':max, 'palette':thermal}
        Map.addLayer(LST.image_pick(img_date), thermal_vis, 'Landsat LST')
        # Map.add_colorbar_branca(colors=thermal, vmin=min, vmax=max, caption = "Surface Temperature (C)", layer_name = 'Surface Temperature')
        Map.add_colorbar(cmap=thermal, vis_params={'bands': ['LST'], 'min': min, 'max': max, 'palette':thermal}, label = "Surface Temperature (C)", layer_name = 'Surface Temperature')
        #Map.addLayer(N_LST.first(), thermal_vis, 'northern swath image')
        Map.to_streamlit(height=800)
    url = LST.image_pick(img_date).getThumbURL({'dimensions':2500, 'format':'png', 'bands':['LST'], 'min':min, 'max':max, 'palette':thermal})
    st.write('Image acquired by', landsat.image_pick(img_date).get('SPACECRAFT_ID').getInfo())
elif dataset_options=='Landsat 8 & 9 Vegetation False Color':
    col7, col8 = st.columns([2, 2])
    with col7:
        min = st.slider('Minimum Display Value', min_value=-500, max_value=5000, value=0, key='min_stretch_value')
    with col8:
        max = st.slider('Maximum Display Value (raise for displaying bright objects)', min_value=10000, max_value=60000, value=24000, key='max_stretch_value') 
    col9, col10, col11 = st.columns([1, 18, 1])
    with col10:  
        Map = geemap.Map(center=(lat, long), zoom=10)
        ls_false_vis = {'bands': ['SR_B5', 'SR_B4', 'SR_B3'], 'min': min, 'max': max, 'gamma': [0.6, 0.6, 0.6]}
        Map.addLayer(landsat.image_pick(img_date), ls_false_vis, 'Landsat false color image')
        Map.to_streamlit(height=800)
    url = landsat.image_pick(img_date).getThumbURL({'dimensions':2500, 'format':'png', 'bands':['SR_B5', 'SR_B4', 'SR_B3'], 'min': min, 'max': max, 'gamma': [0.6, 0.6, 0.6]})
    st.write('North image acquired by', landsat.image_pick(img_date).get('SPACECRAFT_ID').getInfo())
elif dataset_options=='Sentinel 2 True Color':
    col7, col8 = st.columns([2, 2])
    with col7:
        min = st.slider('Minimum Display Value', min_value=-500, max_value=1000, value=0, key='min_stretch_value')
    with col8:
        max = st.slider('Maximum Display Value (raise for displaying bright objects)', min_value=2000, max_value=10000, value=4000, key='max_stretch_value')    
    sn_true_vis = {'bands': ['B4', 'B3', 'B2'], 'min': min, 'max': max} #params for original bands
    col9, col10, col11 = st.columns([1, 18, 1])
    with col10:
        Map = geemap.Map(center=(lat, long), zoom=10)
        Map.addLayer(sentinel.image_pick(img_date), sn_true_vis, 'Sentinel true color imagery')
        Map.to_streamlit(height=800)
    url = sentinel.image_pick(img_date).getThumbURL({'dimensions':2500, 'format':'png', 'bands':['B4', 'B3', 'B2'], 'min': min, 'max': max})


#url = image_grab(landsat_N, N_img_date).getThumbURL({'dimensions':2500, 'format':'jpg', 'bands':['SR_B4', 'SR_B3', 'SR_B2'], 'min': min, 'max': max, 'gamma': [0.6, 0.6, 0.6]})
download = st.button(label='Link to save image png', help='Click button to show link to view and save a png image with a max dimension of 2000px')
if download:
    st.write(url)
#st.write(url_N)
#st.write(url_N)

st.write('*Contact: markradwin@gmail.com*')
st.write('*Affiliation: University of Utah - Geology & Geophysics Dept.*')
st.write('*GitHub Repo: https://github.com/radwinskis/Rad_Gee_Streamlit *')