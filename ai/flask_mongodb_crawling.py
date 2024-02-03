# 크롤링용 라이브러리
import re
import time
import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

# webdriver가 안보이게 설정
options = webdriver.ChromeOptions()
options.add_argument('--headless')

# flask, mongodb 라이브러리
from flask import Flask, jsonify, request
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

app = Flask(__name__)

uri = os.getenv('MONGODB_URI') # 클라우드 환경 시 주석해제
# uri = "mongodb+srv://SQC1415:nlpq8s1514@cluster0.eyigtrn.mongodb.net/SQC?" #로컬 서버 테스트 시 주석해제
# Create a new client and connect to the server

client = MongoClient(uri, server_api=ServerApi('1'))
db = client.SQC

@app.route('/')
# def home():
#     return render_template('index.html')

@app.route('/product', methods=['POST'])
def post_product():
    
    temp_url = 'https://www.musinsa.com/categories/item/018'
    headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    temp_page = requests.get(temp_url, headers=headers)
    temp_soup = BeautifulSoup(temp_page.content, 'html.parser')
    page_num = temp_soup.find('span', {'class': 'totalPagingNum'})
    page_num = int(re.sub('[^0-9]', '', page_num.get_text())) + 1

    # 스니커즈 모든 페이지에 대해서
    for i in range(1, page_num):
        url = 'https://www.musinsa.com/categories/item/018?d_cat_cd=018&brand=&list_kind=small&sort=pop_category&sub_sort=&page='+str(i)+'&display_cnt=90&group_sale=&exclusive_yn=&sale_goods=&timesale_yn=&ex_soldout=&plusDeliveryYn=&kids=&color=&price1=&price2=&shoeSizeOption=&tags=&campaign_id=&includeKeywords=&measure='
        page = requests.get(url, headers=headers)
        page_soup = BeautifulSoup(page.content, 'html.parser')
        
        # 상품의 정보가 있는 html을 가져옴
        product_list = page_soup.find_all('div', {'class': 'article_info'})

        for product in product_list:
            # 리뷰수를 가져오는 함수
            try:
                review_num = product.find('span', {'class':'count'}).get_text()
                review_num = int(re.sub('[^0-9]','',review_num))
            # 없으면 0으로 처리
            except:
                review_num = 0

            # 리뷰수가 50개 이상인 상품의 soup를 가져온다
            if review_num > 49:

                # url 가져오기
                url = 'https:'+product.select('p.list_info > a')[0].attrs['href']

                # 제품명 가져오기
                name = product.find('a', {'name': 'goods_link'})
                name.find('strong').decompose()
                name = name.get_text().replace('\n', ' ').strip()

                # 브랜드명 가져오기
                brand = product.select('p.item_title > a')[0].get_text()

                # 가격 가져오기
                price = product.find('p', {'class': 'price'}).get_text().split()
                if len(price) == 1:
                    # 할인가격 없을시 현재가격
                    price = price[0]
                    price = int(re.sub('[^0-9]', '', price))
                else:
                    # 할인 가격이 있을 시 할인 가격을 추가
                    price = price[1]
                    price = int(re.sub('[^0-9]', '', price))

                # 셀레니움으로 원하는 데이터 가져오기
                driver = webdriver.Chrome(options=options)
                driver.get(url)
                sel_html = driver.page_source
                sel_soup = BeautifulSoup(sel_html)

                # 성별 데이터 가져오기
                sex_html = sel_soup.select('#product-right-top > div.product-detail__sc-achptn-0.eXRtIE > ul > li:nth-child(2) > div.product-detail__sc-achptn-6.gfoaTb > span')
                if len(sex_html) == 3:
                    sex = sex_html[2].get_text()
                else:
                    sex = sex_html[0].get_text()
                
                # 남은 사이즈 정보 가져오기
                if len(sel_soup.select('#option2 > option')) != 0:
                    all_size = []
                    color_num = len(sel_soup.select('#option1 > option'))
                    for i in range(1, color_num):
                        size_list = []
                        select = Select(driver.find_element(By.CSS_SELECTOR, '#option1'))
                        select.select_by_index(i)
                        time.sleep(0.5)

                        color_html = driver.page_source
                        color_soup = BeautifulSoup(color_html)

                        color = color_soup.select('#option1 > option:nth-child('+str(i+1)+')')[0].get_text()
                        color = str(color.split()[0])

                        sizes = color_soup.select('#option2 > option')
                        for size in sizes:
                            size = size.get_text()
                            if size.find('옵션') and size.find('품절') == -1:
                                size_list.append(size)
                                
                        all_size.append({color:size_list})
                        
                else:
                    all_size = []
                    sizes = sel_soup.select('#option1 > option')
                    for size in sizes:
                        size = size.get_text()
                        size = re.sub('[^0-9가-힣\\(\\)]', '', size)
                        if size.find('옵션') and size.find('품절') == -1:
                            all_size.append(size)
                        
                # 제품 사이트 내 태그 가져오기
                tag_html = sel_soup.find_all('a', {'class': 'product-detail__sc-uwu3zm-1 hhzMHa'})
                tag_list =[]

                for tag in tag_html:
                    tag_list.append(tag.get_text()[1:])

                # 좋아요 수 가져오기
                try:
                    like = sel_soup.find_all('span', {'class':'product-detail__sc-achptn-4 flUHrZ'})[0].get_text()
                except:
                    like = ''

                # 조회수 가져오기
                try:
                    view = sel_soup.select('#product-right-top > div.product-detail__sc-achptn-0.eXRtIE > ul > li:nth-child(3) > div.product-detail__sc-achptn-6.gfoaTb > span')[0].get_text()
                except:
                    view = ''

                # 누적 판매 수 가져오기
                try:
                    buy = sel_soup.select('#product-right-top > div.product-detail__sc-achptn-0.eXRtIE > ul > li:nth-child(4) > div.product-detail__sc-achptn-6.gfoaTb > span')[0].get_text()
                except:
                    buy = ''

                # 리뷰 수 가져오기
                try:
                    review = sel_soup.find_all('span', {'id':'review_total'})[0].get_text()
                except:
                    review_num.append('')

                # 스니커즈 사진 가져오기
                try:
                    img = sel_soup.select('#product-left-top > div.product-detail__sc-p62agb-0.lfknLw > div > img')
                    img = img[0].attrs['src']
                except:
                    img = ''
                
                # 드라이버 닫아주기
                driver.close()
                # 시간추가
                time.sleep(0.01)
                    
                product_info = {
                    'brand': brand,
                    'name': name,
                    'tag': tag_list,
                    'sex': sex,
                    'price': price,
                    'size': all_size,
                    'view': view,
                    'buy': buy,
                    'like': like,
                    'review': review,
                    'url': url,
                    'img' : img
                }
                
                db.product.update_one({"name": name}, product_info, upsert=True)
                
    return jsonify({'result': 'success', 'msg': '성공적으로 작성되었습니다'})

@app.route('/findShoesList', methods=['GET'])
def read_product_info():
    name = request.args.get('name', {'$ne': ''})
    if name == "":
        name = {'$ne': ''}
        
    tag = request.args.get('tag', {'$ne': ''})
    if tag == "":
        tag = {'$ne': ''}
    elif ',' in tag:
        tag = tag.split(',')
        tag = {'$all': tag}
    else:
        tag = [tag]
        tag = {'all': tag}
        
    brand = request.args.get('brand', {'$ne': ''})
    if brand == "":
        brand = {'$ne': ''}
        
    sex = request.args.get('sex', {'$ne': ''})
    if sex != {'$ne': ''}:
        sex = {'$regex': sex}
    elif sex == "":
        sex = {'$ne': ''}
        
    size = request.args.get('size', {'$ne': ''}) 
    if size == "":
        size = {'$ne': ''}
        
    minPrice = request.args.get('minPrice', 1000)
    if minPrice == '':
        minPrice = 1000
    minPrice = int(minPrice)
    
    maxPrice = request.args.get('maxPrice', 999999)
    if maxPrice == '':
        maxPrice = 999999
    maxPrice = int(maxPrice)
    
    # mongodb에서 조건에 맞는 data 조회
    # product_infos = list(db.product.find({'name': name, 'tag': tag, 'brand': brand, 'sex': sex, 'size': size, 'price': {'$gte':minPrice},'price': {'$lte':maxPrice}},
    #                                      {'_id': False}))
    # print(product_infos)
    # return jsonify({'result': 'success', 'msg': '성공적으로 상품를 가져왔습니다.', 'infos': product_infos})

    # 첫 번째 문서 가져오기
    first_document = list(db.product.find({'name': name, 'tag': tag, 'brand': brand, 'sex': sex, 'size': size, 'price': {'$gte':minPrice},'price': {'$lte':maxPrice}}, {'_id': True}, sort=[('_id', 1)]))[0]

    # 마지막 문서 가져오기
    last_document = list(db.product.find_one({'name': name, 'tag': tag, 'brand': brand, 'sex': sex, 'size': size, 'price': {'$gte':minPrice},'price': {'$lte':maxPrice}}, {'_id': True}, sort=[('_id', -1)]))[0]

    # 가져온 문서의 _id 값 추출
    first_id = first_document
    last_id = last_document

    # 결과 출력
    response = f"startId: {first_id}, endId: {last_id}"

    return response


@app.route('/showShoesList', methods=['GET'])
def read_info():
    # mongodb에서 모든 데이터 조회
    # product_infos = list(db.product.find({}, {'_id': True}))
    # MongoDB에서 맨 처음과 맨 마지막 문서를 가져오는 쿼리 작성
    first_document = list(db.product.find_one({}, {'_id': True}, sort=[('_id', 1)]))[0]
    last_document = list(db.product.find_one({}, {'_id': True}, sort=[('_id', -1)]))[0]

    # 가져온 문서의 _id 값 추출
    first_id = first_document
    last_id = last_document

    response = f"startId: {first_id}, endId: {last_id}"

    return response
    # return jsonify({'result': 'success', 'msg': '성공적으로 상품를 가져왔습니다.', 'infos': product_infos})

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
                
