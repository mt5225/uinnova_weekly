from time import gmtime, strftime, sleep
import os
from datetime import datetime
import pandas as pd
import numpy as np
import glob
import plotly.graph_objs as go
import plotly.offline as offline
from jinja2 import Environment, FileSystemLoader



def save_img_to_disk():
    ''' Save image to local disk
    '''
    from selenium import webdriver
    profile = webdriver.FirefoxProfile()
    profile.set_preference('browser.download.folderList', 2)  # custom location
    profile.set_preference('browser.download.manager.showWhenStarting', False)
    profile.set_preference('browser.download.dir',
                           '/Users/mt5225/Projects/uinnova/weekly/.')
    profile.set_preference(
        'browser.helperApps.neverAsk.saveToDisk', 'image/png')
    driver = webdriver.Firefox(firefox_profile=profile)
    driver.get("file:////Users/mt5225/Projects/uinnova/weekly/temp-plot.html")
    sleep(2)
    driver.quit()


def cleanup():
    ''' Clean old file
    '''
    try:
        map(os.remove, glob.glob("*.png"))
        os.remove('report.pdf')
        os.remove('out.html')
    except OSError:
        pass


def generate_image(img_name):
    ''' Generate user count image
    '''
    # generate weekly user count chart
    df_user = pd.read_csv("./data/" + img_name + '.csv',  header=None)

    if(img_name == 'top10_user'): 
        data = [
            go.Bar(x=df_user.iloc[:, 0], y=df_user.iloc[:, 1])
        ]
    else:
        data = [
            go.Scatter(x=df_user.iloc[:, 0], y=df_user.iloc[:, 1])
        ]

    offline.plot({'data': data,
                  'layout': {'title': '',
                             'font': dict(size=10)
                            }},
                 image='png',
                 output_type='file',
                 auto_open=False,
                 image_filename=img_name)
    save_img_to_disk()


def generate_pdf(pdf_filename):
    ''' Generate pdf file
    '''
    # load the summary file
    df_summary = pd.read_csv("./data/summary.csv",  header=None)
    env = Environment(loader=FileSystemLoader('.'))

    template = env.get_template("report_tpl.html")

    # generate html
    template_vars = {
        "week_str": 'Jun 21, 2017',
        "summary_table": df_summary.to_html(index=False, header=False)
    }
    html_out = template.render(template_vars)

    with open("out.html", "w") as text_file:
        text_file.write(html_out)

    # generate pdf
    from weasyprint import HTML
    HTML('out.html').write_pdf(
        pdf_filename, stylesheets=["style.css"])


def fetch_data(file_list):
    ''' Fetch data from uinnova.com
    '''
    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('52.27.170.134',
                   username='ubuntu',
                   key_filename='/Users/mt5225/pem/website_en.pem')
    sftp = client.open_sftp()

    result = [sftp.get('/tmp/data/' + i, './data/' + i) for i in file_list]
    sftp.close()

def move_to_desktop(pdf_filename):
    ''' Move the generated weekly report file to Desktop
    '''
    os.rename(pdf_filename, '/Users/mt5225/Desktop/' + pdf_filename)


def main():
    ''' Main entry
    '''
    file_list = ['summary.csv', 'user_weekcount.csv',
                 'scene_weekcount.csv', 'top10_user.csv']

    pdf_filename = 'uDCB_Weekly_Report_' + \
        strftime("%Y_%m_%d", gmtime()) + '.pdf'
    cleanup()
    fetch_data(file_list)
    map(generate_image, [item[:-4] for item in file_list[1:]])
    generate_pdf(pdf_filename)
    move_to_desktop(pdf_filename)
    # send_email('uDCB_Weekly_Report.pdf')


if __name__ == "__main__":
    main()
