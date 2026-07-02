import machine as m, dht, time as t, math as o, sys, uselect

h = m.Pin(25, m.Pin.OUT)
h.value(0)
s = dht.DHT22(m.Pin(27))
a = m.ADC(m.Pin(34))
a.atten(m.ADC.ATTN_11DB)
u = m.UART(2, 9600, tx=17, rx=16, timeout=1000)

p = uselect.poll()
p.register(sys.stdin, uselect.POLLIN)

md, hon, t_st, t_cd, lk, lr = "MANUAL", False, 0, 0, False, 0
l1, l25, l10, ltc = 0, 0, 0, 0.0
# Initialize raw count variables
r03, r05, r10, r25, r50, r100 = 0, 0, 0, 0, 0, 0

def rd_pm():
    if u.any() > 128: u.read(u.any()); return None
    while u.any() >= 32:
        if u.read(1) == b'\x42' and u.read(1) == b'\x4D':
            b = u.read(30)
            if len(b) == 30: 
                # PM values (CF=1)
                p1 = (b[2] << 8) | b[3]
                p25 = (b[4] << 8) | b[5]
                p10 = (b[6] << 8) | b[7]
                # Raw Counts per 0.1L air
                c03 = (b[14] << 8) | b[15]
                c05 = (b[16] << 8) | b[17]
                c10 = (b[18] << 8) | b[19]
                c25 = (b[20] << 8) | b[21]
                c50 = (b[22] << 8) | b[23]
                c100 = (b[24] << 8) | b[25]
                return p1, p25, p10, c03, c05, c10, c25, c50, c100
    return None

while True:
    n = t.ticks_ms()
    if p.poll(10):
        c = sys.stdin.readline().strip().lower()
        if c == "auto": md = "AUTOMATIC"
        elif c == "manual": md = "MANUAL"; h.value(0); hon = False; lk = False
        elif c == "high" and md == "MANUAL": h.value(1); t_st = n; hon = True
        elif c == "low" and md == "MANUAL": h.value(0); hon = False

    # 35-Second Cooldown Logic
    if md == "AUTOMATIC" and hon and t.ticks_diff(n, t_st) >= 5000:
        h.value(0); hon = False; lk = True; t_cd = n
    if lk and t.ticks_diff(n, t_cd) >= 35000:
        lk = False

    if t.ticks_diff(n, lr) >= 2000:
        lr = n
        
        dht_t, dht_h = "Err", "Err"
        try:
            s.measure()
            dht_t = f"{s.temperature()}"
            dht_h = f"{s.humidity()}"
        except: pass
        
        try:
            r = a.read()
            if 50 < r < 4045:
                res = 10000.0 * (r / (4095.0 - r))
                ltc = (1.0 / (o.log(res / 10000.0) / 3950 + (1.0 / 298.15))) - 273.15
        except: pass
        
        pm = rd_pm()
        if pm: 
            l1, l25, l10, r03, r05, r10, r25, r50, r100 = pm

        tgt = hon
        if md == "AUTOMATIC": tgt = True if (dht_h != "Err" and s.humidity() > 40) else False
        
        # 45C Cutoff
        if ltc >= 45.0: tgt = False
        if lk: tgt = False

        if tgt:
            if not hon: t_st = n; hon = True
            h.value(1)
        else:
            h.value(0); hon = False

        if lk: h_stat = "COOLDOWN"
        elif h.value() == 1: h_stat = "ON"
        else: h_stat = "OFF"

        # --- SEND EXTENDED DATA TO WEB APP ---
        # Format: DATA:Mode,Heater,DHT_Temp,DHT_Hum,Therm_Temp,PM1,PM25,PM10,Raw0.3,Raw0.5,Raw1.0,Raw2.5,Raw5.0,Raw10.0
        print(f"DATA:{md},{h_stat},{dht_t},{dht_h},{round(ltc, 1)},{l1},{l25},{l10},{r03},{r05},{r10},{r25},{r50},{r100}")

    t.sleep(0.1)