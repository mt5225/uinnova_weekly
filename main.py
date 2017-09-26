from time import gmtime, strftime, sleep
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import glob
from jinja2 import Environment, FileSystemLoader
import paramiko
import logging

# create logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def cleanup():
    ''' Clean old file
    '''
    try:
        map(os.remove, glob.glob("*.png"))
        map(os.remove, glob.glob("./data/*.csv"))
        os.remove('report.pdf')
        os.remove('out.html')
    except OSError:
        pass


def generate_download_chart(downloads):
    ''' generate download chart
    '''
    df = pd.DataFrame(downloads.items(),columns=['Date', 'Downloads'])
    df['WeekDay'] = ['Sun', 'Mon', 'Tue', 'Web', 'Thur', 'Fri', 'Sat']
    title = "total downloads last week = " + str(df['Downloads'].sum())
    ax = df.plot(kind='bar', x= 'WeekDay' , y='Downloads', title = title, fontsize=6, rot=0)
    for p in ax.patches:
        ax.annotate(str(int(p.get_height())), xy=(p.get_x() + 0.2, p.get_height() + 0.2))
    fig = ax.get_figure()
    fig.savefig('downloads.png')

def generate_image(img_name):
    ''' Generate uDCB statistics image
    '''
    column_names = ['date','value']
    df = pd.read_csv("./data/" + img_name + '.csv',  header=None, names = column_names)
    if(img_name == 'top10_user'):
        img_type = 'bar'
    else:
        img_type = 'line'
    ax = df.plot(kind=img_type, x='date', y='value', title = img_name, rot=-45, fontsize=6)
    fig = ax.get_figure()
    fig.savefig(img_name + '.png')


def generate_pdf(pdf_filename, weekday):
    ''' Generate pdf file
    '''
    # load the summary file
    df_summary = pd.read_csv("./data/summary.csv",  header=None)
    env = Environment(loader=FileSystemLoader('.'))

    template = env.get_template("report_tpl.html")

    # generate html
    template_vars = {
        "week_str": weekday,
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
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('52.27.170.134',
                   username='ubuntu',
                   key_filename='/Users/mt5225/pem/website_en.pem')
    sftp = client.open_sftp()
    result = [sftp.get('/tmp/data/' + i, './data/' + i) for i in file_list]
    sftp.close()

def getLastSevenDays():
    ''' get array of last 7 days
    '''
    today = datetime.now()
    return [ (today + timedelta(days=n)).strftime('%d/%b/%Y')  for n in range(-7,0)]

def run_stat_on_server():
    ''' run stat script on server
    '''
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('52.27.170.134',
                   username='ubuntu',
                   key_filename='/Users/mt5225/pem/website_en.pem')
    client.exec_command('rm -rf /tmp/data/*.csv');
    client.exec_command('/bin/sh /home/ubuntu/scripts/weeklyreport2.sh');
    client.close();

def get_downloads():
    ''' analysis nginx access log to get number of downloads
    '''
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('52.27.170.134',
                   username='ubuntu',
                   key_filename='/Users/mt5225/pem/website_en.pem')
    downloads = {}
    for datestr in getLastSevenDays():
        stdin, stdout, stderr = client.exec_command('grep mmd-v1.2.1.420-en.exe  /var/log/nginx//access.*|grep "' + datestr +'" | wc -l')
        downloads[datestr] = int(stdout.readline())
    client.close()
    return downloads


def move_to_desktop(pdf_filename):
    ''' Move the generated weekly report file to Desktop
    '''
    os.rename(pdf_filename, '/Users/mt5225/Desktop/' + pdf_filename)


def main():
    ''' Main entry
    '''
    # init
    logging.info("cleanup old files")
    cleanup()
    file_list = ['summary.csv', 'user_weekcount.csv',
                 'scene_weekcount.csv', 'top10_user.csv']
    pdf_filename = 'uDCB_Weekly_Report_' + \
        strftime("%Y_%m_%d", gmtime()) + '.pdf'
    weekday = strftime("%Y_%m_%d", gmtime())
    logging.info("generate data file")
    run_stat_on_server()
    logging.info("sleep for 3 secs")
    sleep(3)

    logging.info("fetch data file")
    fetch_data(file_list)

    # generate chart file from data
    logging.info("generate stat chart")
    map(generate_image, [item[:-4] for item in file_list[1:]])

    logging.info("sleep for 3 secs")
    sleep(3)

    logging.info("generate download chart")
    generate_download_chart(get_downloads())
    
    # generate pdf
    logging.info("generate pdf")
    generate_pdf(pdf_filename, weekday)
    move_to_desktop(pdf_filename)

    logging.info("== DONE ==")

if __name__ == "__main__":
    main()
