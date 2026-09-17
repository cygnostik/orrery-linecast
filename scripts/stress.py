"""Deterministic offline adversarial checks; run with the pinned Linecast environment."""
import sys, json, random, time, math, statistics, traceback
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import OrreryApp, State, parse_date, payload
from astronomy import BODIES, MIN_DATE, MAX_DATE, position_at
from linecast import sky
from linecast._graphics import visible_len


results=[]
counts={}

def record(group,label,fn):
    begin=time.perf_counter()
    try:
        fn()
        results.append({'group':group,'case':label,'pass':True,'seconds':time.perf_counter()-begin})
    except Exception as e:
        results.append({'group':group,'case':label,'pass':False,'error':type(e).__name__+': '+str(e),'traceback':traceback.format_exc(limit=4)})

def frame(a,w,h):
    a.width=w;a.height=h
    s=a.render_static();lines=s.splitlines()
    assert len(lines)==h, (len(lines),h)
    wrong=[(i+1,visible_len(l)) for i,l in enumerate(lines) if visible_len(l)!=w]
    assert not wrong,(w,h,wrong[:3])
    return s

moment=parse_date('2026-09-17T05:00:00Z')
sizes=[(1,1),(39,15),(40,16),(59,19),(60,20),(61,21),(79,23),(80,24),(105,29),(106,30),(120,40),(160,50),(300,100)]
for w,h in sizes:
    for body in BODIES:
        for compressed,tilted,zoom in [(True,True,1),(False,False,.3),(True,False,8),(False,True,8)]:
            def check(w=w,h=h,body=body,compressed=compressed,tilted=tilted,zoom=zoom):
                a=OrreryApp(State(moment=moment,playing=False,selected=body['id'],compressed=compressed,tilted=tilted,zoom=zoom),w,h)
                frame(a,w,h)
            record('orbital_layout',f'{w}x{h}/{body["id"]}/{compressed}/{tilted}/{zoom}',check)

with patch('socket.create_connection',side_effect=AssertionError('unexpected network')),patch('socket.socket.connect',side_effect=AssertionError('unexpected network')):
    for date in [MIN_DATE,moment,MAX_DATE]:
        for loc in [(90,180),(-90,-180),(0,0),(34.05,-118.25),(89.999,179.999)]:
            for w,h in [(60,20),(80,24),(106,30),(120,40),(300,100)]:
                def check(date=date,loc=loc,w=w,h=h):
                    original=(sky.get_terminal_size,sky.install_banner)
                    a=OrreryApp(State(moment=date,playing=False,view='sky',location=loc),w,h)
                    frame(a,w,h)
                    for body in BODIES:
                        a.select(body['id'])
                        assert math.isfinite(a.camera.az) and math.isfinite(a.camera.alt)
                    json.dumps(payload(a.state),allow_nan=False)
                    assert original==(sky.get_terminal_size,sky.install_banner)
                record('offline_sky',f'{date.isoformat()}/{loc}/{w}x{h}',check)

rng=random.Random(20260917)
a=OrreryApp(State(moment=moment,playing=False,location=(34.05,-118.25)),120,40)
keys=list('123456789p.,r[]nviut0adwscm+-?lb')
for i in range(1500):
    def check(i=i):
        if a.help_open or a.location_edit:a.intercept('escape')
        key=rng.choice(keys)
        a.intercept('char:'+key)
        if i%7==0:a.advance(rng.random()*12)
        if i%11==0:a.on_wheel(rng.choice([-1,1]),0,0)
        if i%17==0:
            a.on_drag(rng.randint(-80,80),rng.randint(-15,15),False)
            a.on_drag(0,0,True)
        if i%23==0:
            w,h=rng.choice(sizes)
            frame(a,w,h)
        assert MIN_DATE<=a.state.moment<=MAX_DATE
        assert .3<=a.state.zoom<=8
    record('seeded_controls',str(i),check)

for direction,date in [(1,MAX_DATE),(-1,MIN_DATE)]:
    def check(direction=direction,date=date):
        a=OrreryApp(State(moment=date,playing=True,direction=direction),120,40)
        a.advance(1e100)
        assert a.state.moment==date and not a.state.playing
    record('clock_boundary',str(direction),check)

# Quantify rendering only. This is not a cross-machine FPS promise.
bench={}
for mode,loc in [('orbit',None),('sky',(34.05,-118.25))]:
    for w,h in [(80,24),(120,40),(300,100)]:
        a=OrreryApp(State(moment=moment,view=mode,location=loc,playing=False),w,h)
        times=[]
        for _ in range(10):
            start=time.perf_counter();frame(a,w,h);times.append((time.perf_counter()-start)*1000)
        bench[f'{mode}/{w}x{h}']={'median_ms':round(statistics.median(times),2),'max_ms':round(max(times),2)}
for r in results:
    group=counts.setdefault(r['group'],{'pass':0,'fail':0})
    group['pass' if r['pass'] else 'fail']+=1
summary={'total':len(results),'passed':sum(r['pass'] for r in results),'failed':sum(not r['pass'] for r in results),'groups':counts,'benchmark':bench,'failures':[r for r in results if not r['pass']]}

print(json.dumps(summary,indent=2))

raise SystemExit(1 if summary['failed'] else 0)
