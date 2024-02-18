import sqlite3

import pandas

# with open("pid_params_stats.txt", 'a', encoding='utf-8') as txt_file:
#     # row = f"kp={self.kp} ki={self.ki} kd={self.kd} " \
#     #       f"update_time={self.update_time} count_raw_call={self.count_raw_call}\n"
#     row = f"kp;ki;kd;update_time;count_raw_call;hotline_counter;occupy_counter\n"
#     txt_file.write(row)

con = sqlite3.connect("demo_stand_database5.db")
cur = con.cursor()
# cur.execute("CREATE TABLE stat_params (kp, ki, kd, update_time, count_raw_call, hotline_counter, occupy_counter);")

df = pandas.read_csv('pid_params_stats.txt', sep=';')
df.to_sql('stat_params', con, if_exists='append', index=False)

# with open('pid_params_stats.txt', 'r') as fin:  # `with` statement available in 2.5+
#     # csv.DictReader uses first line in file for column headings by default
#     dr = csv.DictReader(fin)  # comma is default delimiter
#     to_db = [(i['col1'], i['col2']) for i in dr]
#
# cur.executemany(" INSERT INTO t (kp, ki, kd, update_time, count_raw_call, hotline_counter, occupy_counter)"
#                 " VALUES (?, ?, ?, ?, ?, ?, ?);", to_db)
con.commit()
con.close()
