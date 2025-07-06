import multiprocessing
multiprocessing.freeze_support()
from seleniummm import WebDriver
import sys
from pathlib import Path
from discord_webhook import DiscordWebhook
from datetime import datetime
import time
import traceback


if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
      # runned executable built by pyinstaller
      root_path = str(Path(sys.executable).parent)
    else:
      root_path = './'
    
    browser = WebDriver(visible=True, 
                # driver_preference='standard',
    )

    def handle_cookie():
      try:
        browser.wait_until_element_presence(tag='kc-global-cookie-banner')
        # cookie
        shadow = browser.find_element(tag='kc-global-cookie-banner').shadow_root
        time.sleep(5)
        cookie_setting_btn = browser.find_element(shadow, id='biscuitPopupBtn')
        browser.click(cookie_setting_btn)
        time.sleep(5)
      except Exception as e:
        print('cookie banner button not found')
        traceback.print_exc()
        return False

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
        time.sleep(5)
        print('cookie handled')
      except Exception as e:
        print('cookie popup processing failed')
        traceback.print_exc()
        return False
      return True

    def login():
      browser.wait_until_element_clickable(css='ke-text-input input')
      id_dom = browser.find_element(css='ke-text-input input')
      id_dom.send_keys()
      pw_dom = browser.find_element(css='ke-password-input input')
      pw_dom.send_keys()
      browser.click(css='.login__submit-act')
      time.sleep(7)
      print('logged in')

    def go_zed_page():
      print('go zed page')
      time.sleep(5)
      shadow = browser.wait_until_element_presence(css='kc-global-floating-button').shadow_root
      zed_btn = browser.find_element(shadow, id='ke-zed-button')
      browser.click(zed_btn)
      browser.sleep(8)
      browser.wait_until_window_number_to_be(2)
      browser.switch_to_window(1)

    def my_zed_itinerary():
      # 나의 항공권으로 이동
      try:
        my_itinerary_btn = browser.wait_until_element_clickable(xpath='//span[text()="나의 항공권"]')
        browser.click(my_itinerary_btn)
      except:
        print('나의 항공권 button not found')
        
      browser.wait_until_element_presence(xpath='//span[text()="예약/리스팅 현황"]')

      time.sleep(5)   # StaleElementReferenceException. maybe refering itinerary before it completed.
      itineraries = browser.find_elements(xpath='//span[text()="예약/리스팅 현황"]/following-sibling::div/div')
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
    
    def send_discord(items, format_string):
      discord = DiscordWebhook(url=)
      content = f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
      for item in items:
        l = format_string.format(**item)
        if(len(content) + len(l) < 2000):
          content += l + '\n'
        else:
          discord.set_content(content)
          discord.execute()
          content = ''
      if len(content) > 0:
        discord.set_content(content)
        discord.execute()


    def go_zed_home():
      browser.get('https://zed.koreanair.com/')
      browser.wait_until_element_clickable(xpath='//span[text()="나의 항공권"]')

    def go_to_oal():
      def conv_date(input_date):
        date_obj = datetime.strptime(f"{input_date} {datetime.now().year}", "%d %B %Y")
        korean_weekdays = ['월', '화', '수', '목', '금', '토', '일']
        weekday_kr = korean_weekdays[date_obj.weekday()]
        return date_obj.strftime("%Y.%m.%d") + f"({weekday_kr})"

      if browser.get_current_url() != 'https://zed.koreanair.com/':
        go_zed_home()

      browser.click(xpath='//button[text()="OAL"]')
      browser.click(xpath='//*[contains(text(), "myIDTravel")]')
      btns = browser.wait_until_elements_visible(xpath='//*[@role="dialog"]//button') # 0: checkbox, 1: 다음
      browser.click(btns[0])
      browser.sleep(1)
      browser.click(btns[1])
      browser.sleep(5)

      browser.wait_until_window_number_to_be(3)
      browser.switch_to_window(2)

      browser.wait_until_element_presence(xpath='//div[@class="modal-content"]')
      browser.click(xpath='//div[@class="modal-content"]//input')
      browser.click(xpath='//div[@class="modal-content"]//button')

      listings = []
      time.sleep(5)
      itineraries = browser.find_elements(xpath='//div[@class[contains(., "_flightCardContainer_")]]')
      for it in itineraries:
        for idx, ch in enumerate(browser.find_children(it, xpath='./div')):
          if idx == 0:  # PNR
            tokens = ch.text.strip().splitlines()
            listing_info = {}
            listing_info['id'] = tokens[1].split(':')[1]
          elif idx == 1: # passengers
            listing_info['passenger'] = ch.text.replace('\n', ', ')
          elif idx == 2: # route
            tokens = ch.text.strip().splitlines()
            listing_info['flt'] = tokens[0]
            listing_info['date'] = conv_date(tokens[1])
            dep_airport = tokens[2].split(' - ')[0]
            arr_airport = tokens[2].split(' - ')[1]
            dep_time = tokens[3].split(' - ')[0].replace(':','')
            arr_time = tokens[3].split(' - ')[1].split(' | ')[0].replace(':','')
            listing_info['dep'] = f"{dep_airport}{dep_time}"
            listing_info['arr'] = f"{arr_airport}{arr_time}"
            listing_info['duration'] = tokens[3].split(' | ')[1].replace(':','')

            # query detail
            expand_btn = browser.find_element(ch, xpath='.//div[@class[contains(., "_containerFlightLoadRBD_")]]')
            browser.mouse_over(expand_btn)
            browser.click(expand_btn)

            detail_popup = browser.wait_until_element_visible(xpath='//div[@class[contains(., "_popupContainer_")]]')
            listing_info['status'] = detail_popup.text.replace('\n', ' ')
            if (cr_point:=listing_info['status'].find('Y')) != -1:
              listing_info['status'] = listing_info['status'][:cr_point-1] + '\n' + listing_info['status'][cr_point:]

            browser.click(expand_btn)
            browser.wait_until_element_invisible(xpath='//div[@class[contains(., "_popupContainer_")]]')

          elif idx == 3:
            listings.append(listing_info.copy())
      return listings

    try:
      browser.get('https://www.koreanair.com/login?returnUrl=%2F')

      if not handle_cookie():
        raise Exception('cookie handling failed')
      
      login()
      go_zed_page()

      listings = my_zed_itinerary()
      send_discord(listings, '[{date} {flt}]\n{passenger} - {status}\n{dep}-{arr}\n({id})---------------')

      oal_listings = go_to_oal()
      send_discord(oal_listings, '[{date} {flt}]\n{status}\n{passenger}\n{dep}-{arr} ({duration})\n({id})---------------')
      

    except Exception as e:
      traceback.print_exc()
      print(traceback.format_exception(e))
       
    finally:
      browser.quit()