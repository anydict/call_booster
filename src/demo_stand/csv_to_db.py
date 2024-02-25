import sqlite3

import pandas  # noqa

content = ''
with open("pid_params_stats.txt", encoding='utf-8') as txt_file:
    content += txt_file.read()
    if 'update_time' not in content:
        content = f"kp;ki;kd;update_time;count_raw_call;hotline_counter;occupy_counter;avg_busy\n" + content

with open("pid_params_stats.txt", mode='w', encoding='utf-8') as txt_file:
    txt_file.write(content)

con = sqlite3.connect("demo_stand_database_avg_busy7.db")
cur = con.cursor()
df = pandas.read_csv('pid_params_stats.txt', sep=';')
df.to_sql('stat_params', con, if_exists='append', index=False)

con.commit()
con.close()
