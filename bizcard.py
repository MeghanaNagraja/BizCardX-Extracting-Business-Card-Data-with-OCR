import easyocr
import cv2
import os
import base64
import io
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import mysql.connector
import streamlit as st
from streamlit_option_menu import option_menu

#Connecting to MySQL and creating table:
connection = mysql.connector.connect(host = 'localhost', password = '', user = 'root', database = 'bizcard')
bccursor = connection.cursor(buffered=True)
bccursor.execute('''CREATE TABLE IF NOT EXISTS business_cards(
        id INT PRIMARY KEY AUTO_INCREMENT,
        company_name VARCHAR(255),
        card_holder_name VARCHAR(255),
        designation VARCHAR(255),
        mobile_number VARCHAR(255),
        email VARCHAR(255),
        website VARCHAR(255), 
        area VARCHAR(255),
        city VARCHAR(255),
        state VARCHAR(255),
        pincode  VARCHAR(255),
        image LONGBLOB       
    )''')

#Extract data and display:
def extract_data(card):
    with open(os.path.join('cards',card.name),'wb') as f:
        f.write(card.getbuffer())
    img_path = os.path.join('cards',card.name)
    reader = easyocr.Reader(['en'], gpu=True)
    result = reader.readtext(img_path)
    return result, img_path

def display_recognition(result, img_path):
    font = cv2.FONT_HERSHEY_SIMPLEX
    img = cv2.imread(img_path)
    for i in result:
        tl = i[0][0]
        tr = i[0][1]
        br = i[0][2]
        txt = i[1]
        img = cv2.rectangle(img,tl,br,(0,255,0),2)
    plt.imshow(img)
    plt.axis('off')
    plt.show()

def structure_data(result):
    text = []
    for i in result:
        itm = []
        itm.append(int(i[0][0][0]))
        itm.append(int(i[0][0][1]))
        itm.append(i[1])    
        text.append(itm)
    text.sort(key = lambda x: x[1])
    card_dict = {}
    mobile = []
    company = []
    website = []
    other = []
    lst = []
    lstt =[]
    tl = None
    for i in text:
        if text.index(i) == 0:
            card_dict['card_holder_name'] = i[2]
            tl = int(i[0])
        elif text.index(i) == 1:
            card_dict['designation'] = i[2]
        elif '@' in i[2]:
            card_dict['email'] = i[2]
        elif 'WWW' in i[2]:
            website.append(i[2])
        elif ('com' or '.com') in i[2]:
            website.append(i[2])
        elif ('www' or 'WWW' or 'www.' or'WWW.') and ('com' or '.com') in i[2]:
            website.clear()
            website.append(i[2])
        elif '-' in i[2]:
            mobile.append(i[2])
            card_dict['mobile_number'] = ' & '.join(mobile)
        elif abs(tl - int(i[0])) > 300:
            company.append(i[2])
            card_dict['company_name'] = ' '.join(company)
        else:
            other.append(i[2])
    for i in other:
        val = i.replace(';','').replace(',','').replace('.','').replace('  ',' ')
        for i in val.split():
            lst.append(i)
    for i in lst:
        if i.isdigit() and (len(i) == 6 or len(i) == 7):
            card_dict['pincode'] = i
        elif lst.index(i) == len(lst)-2:
            card_dict['state'] = i
        elif lst.index(i) == len(lst)-3:
            card_dict['city'] = i
        else:
            lstt.append(i)
    card_dict['area'] = ' '.join(lstt)
    website.sort()
    card_dict['website'] = ''.join(website)
    return(card_dict)

def convert_image(img_path):
    with open(img_path, 'rb') as file:
        cnvrt_data = file.read()
        cnvrt_file = base64.b64encode(cnvrt_data)
        extracted_val['image'] = cnvrt_file

#Building streamlit dashboard to extract data, store, view, modify and delete:
st.set_page_config(layout= "wide",initial_sidebar_state= "expanded")
with st.sidebar:
    st.title('EXTRACTING BUSINESS CARD DATA WITH OCR')
    st.image('img1.png')
    select = option_menu(
        menu_title = "Home",
        options = ['Extract and Upload','View Data','Modify','Delete'],
        default_index = 0,
    )
    st.subheader('Technologies used:')
    st.caption('Python')
    st.caption('MySQL')
    st.caption('Streamlit')
    st.caption('EasyOCR')

if select == 'Extract and Upload':
    st.divider()
    st.markdown("<h1 style='text-align: center; color: black;'>EXTRACT DATA</h1>", unsafe_allow_html=True)
    st.divider()
    st.markdown('<style>div.block-container{padding-top:1rem;}</style>',unsafe_allow_html=True)
    st.subheader("Upload an image to extract data using EasyOCR. You can also migrate it to sql database.")
    card = st.file_uploader('',type=['png','jpg','jpeg'])
    if card:
        result, img_path = extract_data(card)
        st.set_option('deprecation.showPyplotGlobalUse', False)
        st.pyplot(display_recognition(result, img_path))
        extracted_val = structure_data(result)
        st.dataframe(extracted_val)
        if extracted_val:
            if st.button('Migrate to SQL'):
                convert_image(img_path)
                query ='''INSERT INTO business_cards(company_name, card_holder_name, designation, mobile_number,
                       email, website, area, city, state, pincode, image) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'''
                val = (extracted_val['company_name'],
                extracted_val['card_holder_name'],
                extracted_val['designation'],
                extracted_val['mobile_number'],
                extracted_val['email'],
                extracted_val['website'],
                extracted_val['area'],
                extracted_val['city'],
                extracted_val['state'],
                extracted_val['pincode'],
                extracted_val['image'])
                bccursor.execute(query, val)
                connection.commit()
                st.success('upload done')

if select == 'View Data':
    bccursor.execute('''SELECT DISTINCT company_name FROM bizcard.business_cards''')
    comp_lst = bccursor.fetchall()
    company_lst = []
    for i in comp_lst:
        company_lst.append(i[0])
    selected = st.selectbox('Choose a company to view details', company_lst)
    if selected:
        query = f"SELECT * FROM bizcard.business_cards WHERE company_name = '{selected}'"
        bccursor.execute(query)
        val_ab = bccursor.fetchall()
        val_a = pd.DataFrame(val_ab,columns = bccursor.column_names)
        image_a = val_ab[0][11]
        binary_data = base64.b64decode(image_a)
        image_b = Image.open(io.BytesIO(binary_data))
        st.write(val_a)
        st.image(image_b, width=500)
        

if select == 'Modify':
    bccursor.execute('''SELECT DISTINCT company_name FROM bizcard.business_cards''')
    comp_lst = bccursor.fetchall()
    company_lst = []
    for i in comp_lst:
        company_lst.append(i[0])
    selected = st.selectbox('Choose a company to modify details', company_lst)
    if selected:
        query = f"SELECT * FROM bizcard.business_cards WHERE company_name = '{selected}'"
        bccursor.execute(query)
        val = pd.DataFrame(bccursor.fetchall(),columns = bccursor.column_names)
        st.write(val)
        col_list = ['company_name', 'card_holder_name', 'designation', 'mobile_number',
                    'email', 'website', 'area', 'city', 'state', 'pincode']
        selct = st.selectbox('Enter a feild name to modify', col_list)
        query_a = f"SELECT {selct} FROM bizcard.business_cards WHERE company_name = '{selected}'"
        bccursor.execute(query_a)
        old_val = bccursor.fetchall()[0][0]
        user_val = st.text_input('Enter new value','')
        if st.button('Modify'):
            query_b = f"UPDATE bizcard.business_cards SET {selct} = '{user_val}' WHERE {selct} = '{old_val}'"
            bccursor.execute(query_b)
            connection.commit()
            st.success('Data is modified')

if select == 'Delete':
    bccursor.execute('''SELECT DISTINCT company_name FROM bizcard.business_cards''')
    comp_lst = bccursor.fetchall()
    company_lst = ['']
    for i in comp_lst:
        company_lst.append(i[0])
    selected = st.selectbox('Choose a company to delete', company_lst)
    if selected:
        query_a = f"DELETE FROM bizcard.business_cards WHERE company_name = '{selected}'"
        bccursor.execute(query_a)
        connection.commit()
        st.error('Deleted')