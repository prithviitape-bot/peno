from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json, random, secrets, threading, os
rooms={}; lock=threading.Lock(); colors=['red','blue','green','yellow']
def deck():
 d=[{'c':c,'v':v} for c in colors for v in ['0']+2*[str(i) for i in range(1,10)]+2*['Skip','Reverse','+2']]+[{'c':'wild','v':v} for v in ['Wild','+4'] for _ in range(4)];random.shuffle(d);return d
def draw(r,p,n):
 for _ in range(n):
  if not r['deck']:
   r['deck']=r['pile'][:-1];r['pile']=r['pile'][-1:];random.shuffle(r['deck'])
  if r['deck']:p['hand'].append(r['deck'].pop())
def advance(r,n=1):r['turn']=(r['turn']+r['dir']*n)%len(r['players'])
def act(a):
 op=a['op'];code=a.get('room','').upper();token=a.get('token');
 if op=='create':
  code=secrets.token_hex(3).upper();rooms[code]={'players':[],'started':False,'winner':None,'turn':0,'dir':1,'log':'Waiting for players'};op='join'
 r=rooms.get(code)
 if not r:raise ValueError('Room not found')
 if op=='join':
  if r['started'] or len(r['players'])>=8:raise ValueError('Room unavailable')
  token=secrets.token_urlsafe(24);r['players'].append({'id':token,'name':str(a.get('name','Player'))[:24] or 'Player','hand':[],'peno':False})
 p=next((p for p in r['players'] if p['id']==token),None)
 if not p:raise ValueError('Invalid player')
 if op=='start':
  if p!=r['players'][0] or r['started'] or len(r['players'])<2:raise ValueError('Need 2–8 players and host')
  r.update(started=True,deck=deck(),pile=[],turn=0,dir=1)
  for q in r['players']:draw(r,q,7)
  i=next(i for i,c in enumerate(r['deck']) if c['v'].isdigit());r['pile']=[r['deck'].pop(i)];r['color']=r['pile'][-1]['c'];r['log']='Game started'
 if op in ['play','draw','peno']:
  if not r['started'] or r['winner']:raise ValueError('Game not active')
  if op=='peno':
   if len(p['hand'])!=1:raise ValueError('UNO requires one card')
   p['peno']=True;r['log']=p['name']+' called UNO!'
  else:
   if r['players'][r['turn']]!=p:raise ValueError('Not your turn')
   if op=='draw':draw(r,p,1);p['peno']=False;advance(r);r['log']=p['name']+' drew a card'
   else:
    i=int(a['index']);
    if i<0 or i>=len(p['hand']):raise ValueError('Invalid card')
    c=p['hand'][i];v=c['v'];top=r['pile'][-1]
    if c['c'] not in ['wild',r['color']] and v!=top['v']:raise ValueError('Card does not match')
    if v=='+4' and any(x['c']==r['color'] for x in p['hand']):raise ValueError('Draw Four requires no matching color')
    color=a.get('color') if c['c']=='wild' else c['c']
    if color not in colors:raise ValueError('Choose a color')
    if len(p['hand'])==1 and not p['peno']:raise ValueError('Call UNO before your final card')
    p['hand'].pop(i);p['peno']=False;r['pile'].append(c);r['color']=color;r['log']=p['name']+' played '+v
    if not p['hand']:r['winner']=p['name']
    if v=='Reverse':r['dir']*=-1;advance(r,2 if len(r['players'])==2 else 1)
    elif v in ['+2','+4']:advance(r);draw(r,r['players'][r['turn']],int(v[1:]));r['players'][r['turn']]['peno']=False;advance(r)
    else:advance(r,2 if v=='Skip' else 1)
 return {'room':code,'token':token,'host':p==r['players'][0],'started':r['started'],'winner':r['winner'],'players':[{'name':q['name'],'count':len(q['hand']),'me':q==p,'peno':q['peno']} for q in r['players']],'turn':r['turn'],'hand':p['hand'],'top':r.get('pile',[None])[-1],'color':r.get('color'),'log':r['log']}
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(open(os.path.join(os.path.dirname(__file__),'index.html'),'rb').read())
 def do_POST(self):
  try:
   a=json.loads(self.rfile.read(int(self.headers['Content-Length'])));
   with lock:out=act(a)
  except Exception as e:out={'error':str(e)}
  self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(out).encode())
if __name__=='__main__':ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT',8000))),H).serve_forever()
