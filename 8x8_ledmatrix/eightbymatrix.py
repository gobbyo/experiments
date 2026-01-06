#			C	o	l	u	m	n	s	
#		Pin	13	3	4	10	6	11	15	16
#		9	1	2	3	4	5	6	7	8
#	R	14	9	10	11	12	13	14	15	16
#	o	8	17	18	19	20	21	22	23	24
#	w	12	25	26	27	28	29	30	31	32
#	s	1	33	34	35	36	37	38	39	40
#		7	41	42	43	44	45	46	47	48
#		2	49	50	51	52	53	54	55	56
#		5	57	58	59	60	61	62	63	64

import scrolltext
from machine import Pin, RTC

def main():
    day = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    rowpins = [26,18,9,20,2,8,3,6]
    colpins = [19,4,5,22,7,21,17,16]

    stext = scrolltext.scrolldisplay()
    stext.rowpins = rowpins
    stext.colpins = colpins

    rtc = RTC()
    rtc.datetime((2023, 2, 6, 1, 22, 00, 4, 0))

    while True:
        t = rtc.datetime()
        buf = "Today is {0}, {1}. {2}, {3}".format(day[t[3]], month[t[1]], t[2], t[0])
        stext.scrolltext(buf,2)
        time.sleep(1)
        buf = "{0}:{1}".format(t[4], t[5])
        stext.scrolltext(buf,2)

if __name__ == "__main__":
    main()