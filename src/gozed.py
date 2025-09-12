import multiprocessing
multiprocessing.freeze_support()
from seleniummm import WebDriver
import sys, os
from pathlib import Path
from discord_webhook import DiscordWebhook
from datetime import datetime
import time
import traceback
import json
import os
os.environ['LANG'] = 'ko_KR.UTF-8'
os.environ['LC_ALL'] = 'ko_KR.UTF-8'

indicators = {
  'en-US': {
    'KE': {
      'ticket_btn': 'My ticket',
      'status_btn': 'Booking/Standby Status',
      'day': 'd',
      'airport': 'City, airport'
    },
    'OAL': {

    }
  },
  'ko-KR': {
    'KE': {
      'ticket_btn': '나의 항공권',
      'status_btn': '예약/리스팅 현황',
      'day': '일',
      'airport': '도시, 공항'
    },
    'OAL': {

    }
  }
}
indicators['en'] = indicators['en-US']
indicators['ko'] = indicators['ko-KR']
locale = 'ko'

if __name__ == '__main__':
    def handle_cookie():
      try:
        browser.wait_until_element_presence(tag='kc-global-cookie-banner')
        # cookie
        shadow = browser.find_element(tag='kc-global-cookie-banner').shadow_root
        time.sleep(10)
        cookie_setting_btn = browser.find_element(shadow, id='biscuitPopupBtn')
        browser.click(cookie_setting_btn)
        time.sleep(10)
      except Exception as e:
        print('cookie banner button not found')
        traceback.print_exc()

      try:
        browser.wait_until_element_presence(css='.hydrated')
        shadow = browser.find_element(tag='kc-global-cookie-banner').shadow_root
        popup_shadow = browser.find_element(shadow, css='.hydrated').shadow_root
        options = browser.find_elements(popup_shadow, css='button.switch')
        for opt in options:
          if opt.get_attribute('aria-pressed') == 'true':
            browser.click(opt)
        confirm_btn = browser.find_element(popup_shadow, css='button.confirm')
        browser.click(confirm_btn)
        time.sleep(10)
        print('cookie handled')
      except Exception as e:
        print('cookie popup processing failed')
        traceback.print_exc()

    def login():
      try:
        browser.wait_until_element_clickable(css='ke-text-input input')
        id_dom = browser.find_element(css='ke-text-input input')
        id_dom.send_keys(priv['KE']['id'])
        pw_dom = browser.find_element(css='ke-password-input input')
        pw_dom.send_keys(priv['KE']['pw'])
        browser.click(css='.login__submit-act')
        time.sleep(10)
        print('logged in')
      except:
        print('login failed')
        traceback.print_exc()


    def go_zed_page():
      print('go zed page')
      time.sleep(10)
      try:
        shadow = browser.wait_until_element_presence(css='kc-global-floating-button').shadow_root
        zed_btn = browser.find_element(shadow, id='ke-zed-button')
        lastWndCnt = len(browser.driver.window_handles)
        browser.click(zed_btn)
        browser.sleep(10)
        browser.wait_until_window_number_to_be(lastWndCnt+1)
        browser.switch_to_window(lastWndCnt)
      except:
        print('임직원 button not found')
        traceback.print_exc()

    def my_zed_itinerary():
      print('my zed itinerary')
      # 나의 항공권으로 이동
      try:
        my_itinerary_btn = browser.wait_until_element_clickable(xpath='//span[text()="' + indicators[locale]['KE']['ticket_btn'] + '"]')
        browser.click(my_itinerary_btn)
      except:
        print('나의 항공권 button not found')
        traceback.print_exc()
      
      time.sleep(10)
      browser.wait_until_element_presence(xpath='//span[text()="' + indicators[locale]['KE']['status_btn'] + '"]')

      time.sleep(15)   # StaleElementReferenceException. maybe refering itinerary before it completed.
      itineraries = browser.find_elements(xpath='//span[text()="' + indicators[locale]['KE']['status_btn'] + '"]/following-sibling::div/div')
      listings = []
      for it in itineraries:
        for idx, ch in enumerate(browser.find_children(it, xpath='./div')):
          if not ch.is_displayed():
            browser.page_down()
            browser.sleep(1)

          if idx == 0:  # AUTH type
            tokens = ch.text.strip().splitlines()
            listing_info = {}
            listing_info['id'] = tokens[0]
            listing_info['passenger'] = tokens[1]
            listing_info['auth_type'] = tokens[2]
          elif idx == 1:  # routes
            routes = browser.find_children(ch, xpath='./div')
            for route in routes:
              tokens = route.text.strip().splitlines()
              listing_info['status'] = tokens[1]
              listing_info['dday'] = tokens[0]
              listing_info['date'] = tokens[2]
              listing_info['dep'] = f'{tokens[3]}{tokens[4].replace(":","")}'
              listing_info['arr'] = f'{tokens[6]}{tokens[7].replace(":","")}'
              if tokens[8][0] in ['+', '-']:
                listing_info['arr'] += tokens[8].replace("일", "")
              listing_info['flt'] = tokens[-2]
              listings.append(listing_info.copy())
      return listings
    
    def notice_error(comment=None):
      discord = DiscordWebhook(url=priv['Discord']['monitor'])
      content = f'====== {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} =====\n'
      if comment != None:
        content += comment + '\n'
      endline = '=' * (len(content)-1) + '\n'
      lines = traceback.format_exc().split('\n')
      for l in lines:
        if(len(content) + len(l) < 2000):
          content += l + '\n'
        else:
          discord.set_content(content)
          discord.execute()
          print(content)
          content = l + '\n'
      content += endline
      discord.set_content(content)
      discord.execute()
      print(content)

    def notice_data(items, format_string):
      discord = DiscordWebhook(url=priv['Discord']['notice'])
      if(items == None or len(items) == 0):
        content = "nothing to send"
      else:
        content = f'====== {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} =====\n'
        endline = '=' * (len(content)-1) + '\n'
        for item in items:
          l = format_string.format(**item)
          if(len(content) + len(l) < 2000):
            content += l + '\n'
          else:
            discord.set_content(content)
            discord.execute()
            content = l + '\n'
        content += endline
      discord.set_content(content)
      discord.execute()


    def go_zed_home():
      print('go zed home')
      try:
        if(browser.get_current_url() != 'https://www.koreanair.com/'):
          print('go to homepage')
          browser.get('https://www.koreanair.com/')
        go_zed_page()
        browser.wait_until_element_clickable(xpath='//span[text()="' + indicators[locale]['KE']['ticket_btn'] + '"]')
      except:
        print('go zed home failed')
        traceback.print_exc()


    def go_to_oal():
      print('go to oal')
      def conv_date(input_date):
        date_obj = datetime.strptime(f"{input_date} {datetime.now().year}", "%d %B %Y")
        korean_weekdays = ['월', '화', '수', '목', '금', '토', '일']
        weekday_kr = korean_weekdays[date_obj.weekday()]
        return date_obj.strftime("%Y.%m.%d") + f"({weekday_kr})"

      if browser.get_current_url() != 'https://zed.koreanair.com/':
        go_zed_home()
        
      time.sleep(10)
      try:
        lastWndCnt = len(browser.driver.window_handles)
        browser.click(xpath='//button[text()="OAL"]')
        browser.click(xpath='//*[contains(text(), "myIDTravel")]')

        # EULA
        print('myIDTravel EULA')
        btns = browser.wait_until_elements_visible(xpath='//*[@role="dialog"]//button') # 0: checkbox, 1: 다음
        browser.click(btns[0])
        browser.sleep(3)
        browser.click(btns[1])
        browser.sleep(5)

        browser.wait_until_window_number_to_be(lastWndCnt+1)
        browser.switch_to_window(lastWndCnt)

        browser.wait_until_element_presence(xpath='//div[@class="modal-content"]')
        browser.click(xpath='//div[@class="modal-content"]//input')
        browser.click(xpath='//div[@class="modal-content"]//button')

        listings = []
        time.sleep(10)
        itineraries = browser.find_elements(xpath='//div[@class[contains(., "_flightCardContainer_")]]')
        for it in itineraries:
          for idx, ch in enumerate(browser.find_children(it, xpath='./div')):
            # print(f'{idx} - {ch.text}')
            if idx == 0:  # PNR
              tokens = ch.text.strip().splitlines()
              listing_info = {}
              try:
                listing_info['id'] = tokens[1].split(':')[1]
              except:
                listing_info['id'] = tokens[1]
            elif idx == 1: # border
              continue
            elif idx == 2: # passengers
              listing_info['passenger'] = ch.text.replace('\n', ', ')
            elif '_startPageFlightCardContainer_' in ch.get_attribute('class'): # route
              routes = browser.find_elements(ch, xpath='.//div[@class[contains(., "_startPageFlightCardDetails_")]]')
              for route in routes:
                tokens = route.text.strip().splitlines()
                listing_info['flt'] = tokens[0]
                listing_info['date'] = conv_date(tokens[1])
                dep_airport = tokens[2].split(' - ')[0]
                arr_airport = tokens[2].split(' - ')[1]
                dep_time = tokens[3].split(' - ')[0].replace(':','')
                arr_time = tokens[3].split(' - ')[1].split(' | ')[0].replace(':','')
                listing_info['dep'] = f"{dep_airport}{dep_time}"
                listing_info['arr'] = f"{arr_airport}{arr_time}"
                listing_info['duration'] = tokens[3].split(' | ')[1].replace(':','')
                listing_info['booking_cls'] = tokens[4]

                # query detail
                expand_btn = browser.find_element(route, xpath='.//div[@class[contains(., "_containerFlightLoadRBD_")]]')
                for i in range(0, 100):
                  try:
                    browser.click(expand_btn)
                    break
                  except:
                    browser.find_element(tag='body').send_keys("\ue015")  # Keys.DOWN
                    browser.mouse_over(expand_btn)
                    time.sleep(5)

                detail_popup = browser.wait_until_element_visible(xpath='//div[@class[contains(., "_popupUpcomingContainer_")]]')
                listing_info['status'] = detail_popup.text.replace('\n', ' ')
                if (cr_point:=listing_info['status'].find('Y')) != -1:
                  listing_info['status'] = listing_info['status'][:cr_point-1] + '\n' + listing_info['status'][cr_point:]

                browser.click(expand_btn)
                time.sleep(3)
                browser.wait_until_element_invisible(xpath='//div[@class[contains(., "_popupUpcomingContainer_")]]')
                listings.append(listing_info.copy())  
        return listings
      except:
        print('go to oal failed')
        traceback.print_exc()
        return None

    # port: IATA Code (capital)
    # date: YYYYMMDD
    def query_zed_status(dep_port, arr_port, dep_date, arr_date):
      print(f'query zed status: {dep_port}->{arr_port} ({dep_date}~{arr_date})')
      go_zed_home()
      result = {
        dep_port,
        arr_port,
        dep_date,
        arr_date
      }

      def find_calendar(year, month):
        for i in range(5):  # it may not start with today. move to leftest calendar.
          arrows = browser.find_elements(xpath='//div[@data-side="bottom"]/div/div/div//*[name()="svg"]')
          browser.click(arrows[0])
          time.sleep(2)

        for i in range(5):
          calenders = browser.wait_until_elements_presence(xpath='//div[@data-side="bottom"]/div/div/div')
          if f'{year}.{month}' in calenders[0].text:
            return calenders[0]
          elif'{year}.{month}' in calenders[1].text:
            return calenders[1]
          else:
            right_arrow = browser.find_element(calenders[1], xpath='.//*[name()="svg"]')
            browser.click(right_arrow)
          time.sleep(2)
        return None
      
      def select_date_in_calendar(year, month, day):
        try:
          calendar = find_calendar(year, month)
          if(calendar == None):
            print('given date is not in window')
            return False

          day_dom = browser.find_element(calendar, xpath='.//span[text()="' + day + '"]')
          browser.click(day_dom)
          return True
        except:
          print('select date failed')
          traceback.print_exc()
          return False

      
      try:
        dep_year = dep_date[:4]
        dep_month = dep_date[4:6]
        dep_day = dep_date[6:]
        arr_year = arr_date[:4]
        arr_month = arr_date[4:6]
        arr_day = arr_date[6:]

        # 0: dep_port
        # 1: arr_port
        # 2: dep/arr date
        # 3: passenger
        input_doms = browser.find_elements(xpath='//button[@aria-haspopup="dialog"]')
        
        # dep_port
        browser.click(input_doms[0])
        browser.wait_until_element_clickable(xpath='//input[@placeholder="' + indicators[locale]['KE']['airport'] + '"]').send_keys(dep_port)
        browser.click(browser.wait_until_element_clickable(xpath=f'//div[@data-value="{dep_port}"]'))

        # arr_port
        browser.click(input_doms[1])
        browser.wait_until_element_clickable(xpath='//input[@placeholder="' + indicators[locale]['KE']['airport'] + '"]').send_keys(arr_port)
        browser.click(browser.wait_until_element_clickable(xpath=f'//div[@data-value="{arr_port}"]'))

        # dep/arr date
        browser.click(input_doms[2])  # open calendar
        # select dep date calendar

        if select_date_in_calendar(dep_year, dep_month, dep_day) == False:
          print('cannot select depature date in calendar')
          return result
        
        if select_date_in_calendar(arr_year, arr_month, arr_day) == False:
          print('cannot select arrival date in calendar')
          return result

      except:
        print('query zed status failed')
        traceback.print_exc()
        return result

    browser = None
    try:
      if getattr(sys, 'frozen', False):
        # runned executable built by pyinstaller
        root_path = str(Path(sys.executable).parent)
      else:
        root_path = './'

      try:
        with open(root_path + 'settings.json') as settings_file:
          settings = json.load(settings_file)
        with open(root_path + 'priv.json', mode="rt") as priv_file:
          priv = json.load(priv_file)
        with open(root_path + 'queries.json', mode="rt") as queries_file:
          queries = json.load(queries_file)
        
      except Exception as e:
        notice_error('configuration file loading failed.')
        raise e
      
      browser = WebDriver(visible=True, 
                  # driver_preference='standard',
                # profile=settings['ChromeProfile']
      )
      browser.get('https://www.koreanair.com/login?returnUrl=%2F')

      handle_cookie()      
      login()
      go_zed_page()

      listings = my_zed_itinerary()
      notice_data(listings, '[{date} {flt} ({id})]\n{dep}-{arr}\n{passenger} - {status}')

      # if 'reservation' in queries['query'].keys():
      #   for q in queries['reservation']:
      #     if q['ZedType'] != 'KE':
      #       continue

      #     query_zed_status(q['DepPort'], q['ArrPort'], q['DepDate'], q['ReturnDate'])

      oal_listings = go_to_oal()
      notice_data(oal_listings, '[{date} {flt} ({id})]\n{dep}-{arr} ({duration})\n{status}\n{passenger} (CLS: {booking_cls})')
      
    except Exception as e:
      traceback.print_exc()
      notice_error()
       
    finally:
      if browser:
        browser.quit()