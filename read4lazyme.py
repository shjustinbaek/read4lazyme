#import library
from selenium import webdriver
from bs4 import BeautifulSoup
import re
import os
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import datetime

#default 날짜 설정
today = datetime.datetime.now()

class user:
    def __init__(self, username, pw, email, emailpw, checked_until = '2018.12.20'):
        self.username = username
        self.pw = pw
        self.email = email
        self.emailpw = emailpw
        self.checked_until = checked_until
        self.browser = webdriver.Chrome(executable_path=r"C:\Users\naval\Downloads\chromedriver_win32\chromedriver.exe")
    def login(self):
        url = "https://yscec.yonsei.ac.kr"
        self.browser.get(url)
        login = self.browser.find_element_by_id("username")
        login.click()
        login.send_keys(self.username)
        login = self.browser.find_element_by_id("password")
        login.click()
        login.send_keys(self.pw)
        login = self.browser.find_element_by_id("loginbtn")
        login.click()
    def get_notice(self):
        page_source = self.browser.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        e = soup.find("a", {"class": "menu-coursebbs"})
        self.browser.get(e['href'])
        page_source = self.browser.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        bottom_list = soup.select("div.table-footer-area > div > ul > li > a")
        if len(bottom_list) > 1:
            page_num = bottom_list[-1].get_text()
            page_link = []
            for i in range(int(page_num)):  # make exception for a single page
                page_link.append(bottom_list[1]['href'][:-1] + str(i + 1))
        else:
            page_link = self.browser.current_url
        all_notice = []
        for page in page_link:
            self.browser.get(page)
            page_source = self.browser.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            notice = soup.find_all("li", {"style": "width:calc(100% - 20px) !important;", "class": ""})
            for i in notice:
                temp = i.get_text()
                ct = temp.split(u"\xa0")[0]
                d = temp.split(u"\xa0")[1]
                course = re.search(r"\[(\[([ :가-힣A-Za-z0-9_]+)\])?([ :가-힣A-Za-z0-9_]+)\]", ct).group(0)
                title = ct.replace(course, '').strip()
                date = re.search(r"([ 가-힣A-Za-z0-9_]+)\,", d).group(0)
                href = i.find('a', href=True)['href']
                temp2 = []
                temp2.append(course)
                temp2.append(title)
                temp2.append(date)
                temp2.append(href)
                all_notice.append(temp2)
        #DataFrame으로 저장, 기존 데이터와 비교
        yscec_data = pd.DataFrame(all_notice, columns=['course', 'title', 'date', 'href'])  
        unread = pd.DataFrame()
        if not os.path.exists('yscec_data_{}.txt'.format(self.username)):
            yscec_data.to_csv('yscec_data_{}.txt'.format(self.username), index=False)
            unread = yscec_data
        else:
            prev_data = pd.read_csv('yscec_data_{}.txt'.format(self.username))
            unread = pd.concat([prev_data, yscec_data])
            unread = unread.drop_duplicates(keep=False, subset="href")
            yscec_data.to_csv("yscec_data_{}.txt".format(self.username), index=False)
        # 메일 보낼 txt 파일 작성
        with open("yscec_mail_{}.txt".format(self.username), 'w', encoding='utf-8') as f:
            f.write("{:^20}".format("YSCEC 새로운 공지사항:\n"))
            f.write("{:^20} {:^50} {:^15} {:^70}\n".format('course', 'title', 'date', 'href'))
            for i in range(len(unread)):
                line = "{:^20} {:^50} {:^15} {:^70}\n".format(unread.loc[i]['course'], unread.loc[i]['title'],
                                                              unread.loc[i]['date'][:-1], unread.loc[i]['href'])
                f.write(line)
    def include_yonsei(self):
        #include yonsei.ac.kr notice
        self.checked_until = yonsei_notice(self.checked_until, self.username)
    def sendmail(self):
        fromaddr = self.email
        toaddrs = self.email
        with open("yscec_mail_{}.txt".format(self.username), "r", encoding='utf-8') as f:
            temptxt = f.read()
            temptxt = temptxt.replace('\n', '<br>')
        username = self.email.split('@')[0]  # without @gmail.com only write Google Id.
        password = self.emailpw
        msg = MIMEMultipart('alternative')
        msg.set_charset('utf8')
        msg['FROM'] = fromaddr
        msg['Subject'] = Header("새로운 공지사항".encode('utf-8'), 'UTF-8').encode()
        msg['To'] = toaddrs
        _attach = MIMEText(temptxt.encode('utf-8'), 'html', 'UTF-8')
        msg.attach(_attach)
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.starttls()
        server.login(username, password)
        server.sendmail(fromaddr, toaddrs, msg.as_string())
        server.quit()


def yonsei_notice(lastday,username):
    #yonsei.ac.kr 공지사항 크롤링
    browser = webdriver.Chrome(executable_path=r"C:\Users\naval\Downloads\chromedriver_win32\chromedriver.exe")
    url = "https://www.yonsei.ac.kr/sc/support/notice.jsp"
    browser.get(url)

    notice_list = []
    base_href = 'https://www.yonsei.ac.kr/sc/support/notice.jsp'
    switch = True
    loop_limit = 0
    #lastday = '2018.11.01'  # 처음 실행할 때만 필요하다
    while switch:
        page_source = browser.page_source
        soup = BeautifulSoup(page_source, "html.parser")

        main_board = soup.find("ul", {"class": "board_list"})
        all_notice = main_board.find_all("li", {"class": ""})
        for notice in all_notice:
            href = base_href + notice.find('a', href=True)['href']
            temp = notice.get_text().strip()
            title = re.search(r"(.+\n)", temp).group(0).strip()
            date = re.search(r"([0-9]{4}\.[0-9]{2}\.[0-9]{2})", temp).group(0)
            notice_list.append([title, date, href])
            if lastday > date:
                switch = False  # false가 되도 for loop은 다 돌아감, 즉 현재 페이지에 있는 모든 공지사항이 notice_list에 저장된다(문제는 안댐)
        next_page = 'https://www.yonsei.ac.kr' + soup.find('a', {'class': 'ico_comm btn_next'})['href']
        browser.get(next_page)
        loop_limit += 1
        if loop_limit > 30:
            break
    checked_until = notice_list[0][1]
    # 데이터 정리
    yonsei_notice = pd.DataFrame(notice_list, columns=['title', 'date', 'href'])
    new_notice = pd.DataFrame()
    if not os.path.exists("yonsei_notice_{}.txt".format(username)):
        yonsei_notice.to_csv("yonsei_notice_{}.txt".format(username), index=False)
        new_notice = yonsei_notice
    else:
        prev_notice = pd.read_csv("yonsei_notice_{}.txt".format(username))
        new_notice = pd.concat([prev_notice, yonsei_notice])
        new_notice = new_notice.drop_duplicates(keep=False, subset="href")
        yonsei_notice.to_csv("yonsei_notice_{}.txt".format(username), index=False)
    with open("yscec_mail_{}.txt".format(username), 'a', encoding='utf-8') as f:
        f.write("{:^20}".format("Yonsei.ac.kr 새로운 공지사항:\n"))
        f.write("{:^50} {:^15} {:^70}\n".format('title', 'date', 'href'))
        for i in range(len(new_notice)):
            line = "{:^50} {:^15} {:^70}\n".format(new_notice.loc[i]['title'], new_notice.loc[i]['date'],
                                                   new_notice.loc[i]['href'])
            f.write(line)
    return checked_until




















######## Code Below does the same task (What i used to test my code above)###############


# 브라우저 키기
browser = webdriver.Chrome(executable_path=r"C:\Users\naval\Downloads\chromedriver_win32\chromedriver.exe")

######################### Yscec 로그인 #############################
url = "https://yscec.yonsei.ac.kr"
browser.get(url)

# 로그인이 안되어 있을 때: 새로 로그인 (추후 if문 사용)
login = browser.find_element_by_id("username")
login.click()
login.send_keys("") #YSCEC ID

login = browser.find_element_by_id("password")
login.click()
login.send_keys("") #YSCEC PW

login = browser.find_element_by_id("loginbtn")
login.click()

######################  Yscec  공지사항 크롤링  #####################
page_source = browser.page_source
soup = BeautifulSoup(page_source, "html.parser")
e = soup.find("a", {"class" :"menu-coursebbs"})
browser.get(e['href'])

page_source = browser.page_source
soup = BeautifulSoup(page_source, "html.parser")
bottom_list = soup.select("div.table-footer-area > div > ul > li > a")

if len(bottom_list) > 1:
    page_num = bottom_list[-1].get_text()
    page_link = []
    for i in range(int(page_num)):  #make exception for a single page
        page_link.append(bottom_list[1]['href'][:-1]+str(i+1))
else:
    page_link = browser.current_url

all_notice = []
for page in page_link:
    browser.get(page)
    page_source = browser.page_source
    soup = BeautifulSoup(page_source, "html.parser")
    notice = soup.find_all("li", {"style":"width:calc(100% - 20px) !important;", "class": ""})
    for i in notice:
        temp = i.get_text()
        ct = temp.split(u"\xa0")[0]
        d = temp.split(u"\xa0")[1]
        course = re.search(r"\[(\[([ :가-힣A-Za-z0-9_]+)\])?([ :가-힣A-Za-z0-9_]+)\]",ct).group(0)
        title = ct.replace(course,'').strip()
        date = re.search(r"([ 가-힣A-Za-z0-9_]+)\,",d).group(0)
        href = i.find('a', href=True)['href']
        temp2 = []
        temp2.append(course)
        temp2.append(title)
        temp2.append(date)
        temp2.append(href)
        all_notice.append(temp2)

#################### DataFrame으로 저장, 기존 데이터와 비교, 메일 보낼 txt 파일 작성 ###########
yscec_data = pd.DataFrame(all_notice, columns=['course', 'title', 'date','href'])  #개수가 안맞는다?
if not os.path.exists('yscec_data.txt'):
    yscec_data.to_csv("yscec_data.txt", index=False)

prev_data = pd.read_csv("yscec_data.txt")
unread = pd.concat([prev_data,yscec_data])
unread = unread.drop_duplicates(keep=False, subset="href")

yscec_data.to_csv("yscec_data.txt", index=False)

#모양이 조금 이상하다?
with open("yscec_mail.txt", 'w', encoding='utf-8') as f:
    f.write("{:^20}".format("YSCEC 새로운 공지사항:\n"))
    f.write("{:^20} {:^50} {:^15} {:^70}\n".format('course','title','date','href'))
    for i in range(len(unread)):
        line = "{:^20} {:^50} {:^15} {:^70}\n".format(unread.loc[i]['course'],unread.loc[i]['title'],unread.loc[i]['date'][:-1],unread.loc[i]['href'])
        f.write(line)


########################### yonsei.ac.kr 공지사항 크롤링 ############################
url = "https://www.yonsei.ac.kr/sc/support/notice.jsp"
browser.get(url)

notice_list = []
base_href = 'https://www.yonsei.ac.kr/sc/support/notice.jsp'
switch = True
loop_limit = 0
lastday = '2018.11.01' #처음 실행할 때만 필요하다
while switch:
    page_source = browser.page_source
    soup = BeautifulSoup(page_source, "html.parser")

    main_board = soup.find("ul", {"class":"board_list"})
    all_notice = main_board.find_all("li", {"class":""})
    for notice in all_notice:
        href = base_href + notice.find('a',href=True)['href']
        temp = notice.get_text().strip()
        title = re.search(r"(.+\n)", temp).group(0).strip()
        date = re.search(r"([0-9]{4}\.[0-9]{2}\.[0-9]{2})",temp).group(0)
        notice_list.append([title, date, href])
        if lastday > date:
            switch = False  #false가 되도 for loop은 다 돌아감, 즉 현재 페이지에 있는 모든 공지사항이 notice_list에 저장된다(문제는 안댐)
    next_page = 'https://www.yonsei.ac.kr'+soup.find('a',{'class':'ico_comm btn_next'})['href']
    browser.get(next_page)
    loop_limit += 1
    if loop_limit > 30:
        break
lastday = notice_list[0][1]  #feature i need later la

# 데이터 정리
yonsei_notice = pd.DataFrame(notice_list, columns=['title','date','href'])
if not os.path.exists('yonsei_notice.txt'):
    yonsei_notice.to_csv("yonsei_notice.txt", index=False)

prev_notice = pd.read_csv("yonsei_notice.txt")
new_notice = pd.concat([prev_notice,yonsei_notice])
new_notice = new_notice.drop_duplicates(keep=False, subset="href")

yonsei_notice.to_csv("yonsei_notice.txt", index=False)

with open("yscec_mail.txt", 'a', encoding='utf-8') as f:
    f.write("{:^20}".format("Yonsei.ac.kr 새로운 공지사항:\n"))
    f.write("{:^50} {:^15} {:^70}\n".format('title','date','href'))
    for i in range(len(new_notice)):
        line = "{:^50} {:^15} {:^70}\n".format(new_notice.loc[i]['title'],new_notice.loc[i]['date'],new_notice.loc[i]['href'])
        f.write(line)


############################# 이메일 보내기 ################################
fromaddr = '' #보낼 메일
toaddrs  = '' #받을 메일 

#gonna need a bit more formating
with open("yscec_mail.txt", "r", encoding='utf-8') as f:
    temptxt = f.read()
    temptxt = temptxt.replace('\n','<br>')

username = '' #without @gmail.com only write Google Id.
password = ''

msg = MIMEMultipart('alternative')

msg.set_charset('utf8')

msg['FROM'] = fromaddr
msg['Subject'] = Header("YSCEC 공지사항".encode('utf-8'),'UTF-8').encode()
msg['To'] = toaddrs


_attach = MIMEText(temptxt.encode('utf-8'), 'html', 'UTF-8')
msg.attach(_attach)

server = smtplib.SMTP('smtp.gmail.com:587')
server.starttls()
server.login(username,password)
server.sendmail(fromaddr, toaddrs, msg.as_string())
server.quit()
