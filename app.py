import os,re,secrets,sqlite3
from contextlib import closing
from datetime import datetime,timezone
from functools import wraps
from decimal import Decimal,InvalidOperation
from flask import Flask,g,request,session,redirect,url_for,render_template,flash,abort
from werkzeug.security import generate_password_hash,check_password_hash
ROOT=os.path.dirname(os.path.abspath(__file__)); DEFAULT_DB_DIR='/tmp' if os.environ.get('VERCEL') else ROOT; DB_PATH=os.environ.get('STOCKFLOW_DB',os.path.join(DEFAULT_DB_DIR,'stockflow.db'))
app = Flask(__name__)
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError(
        "SECRET_KEY must be configured before starting StockFlow."
    )
app.config.update(
    SECRET_KEY=secret_key,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    MAX_CONTENT_LENGTH=1048576,
)
def connect_db():
 d=sqlite3.connect(DB_PATH);d.row_factory=sqlite3.Row;d.execute('PRAGMA foreign_keys=ON');return d
def init_db():
 with closing(connect_db()) as d:
  with d:d.executescript()
def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def organization_name_error(name):
 if not name or len(name) < 2 or len(name) > 80:
  return 'Organization name must be between 2 and 80 characters.'
 if any(ord(ch) < 32 or 127 <= ord(ch) < 160 for ch in name):
  return 'Organization name cannot contain control characters.'
 if not any(ch.isalnum() for ch in name):
  return 'Organization name must contain at least one letter or number.'
 return None
def password_error(password):
 if len(password) < 8 or len(password) > 128:
  return 'Password must be between 8 and 128 characters.'
 if not re.search(r'[A-Z]', password):
  return 'Password must include at least one capital letter (A–Z).'
 if not re.search(r'[a-z]', password):
  return 'Password must include at least one lowercase letter (a–z).'
 if not re.search(r'[0-9]', password):
  return 'Password must include at least one number (0–9).'
 if not re.search(r'[^A-Za-z0-9\s]', password):
  return 'Password must include at least one special character (for example !, @, #, or $).'
 return None
def csrf_token():
 if '_csrf' not in session:session['_csrf']=secrets.token_urlsafe(32)
 return session['_csrf']
app.jinja_env.globals['csrf_token']=csrf_token
@app.before_request
def before():
 g.db=connect_db();uid=session.get('user_id');g.user=g.db.execute('SELECT u.id,u.email,u.organization_id,o.name organization_name,o.default_threshold FROM users u JOIN organizations o ON o.id=u.organization_id WHERE u.id=?',(uid,)).fetchone() if uid else None
 if request.method=='POST' and (not request.form.get('_csrf') or not secrets.compare_digest(request.form.get('_csrf',''),session.get('_csrf',''))):abort(400,'Invalid or missing CSRF token.')
@app.teardown_request
def teardown(exc):
 d=g.pop('db',None)
 if d:d.close()
def required(fn):
 @wraps(fn)
 def w(*a,**kw):
  if not g.user:return redirect(url_for('login'))
  return fn(*a,**kw)
 return w
def owned(pid):return g.db.execute('SELECT * FROM products WHERE id=? AND organization_id=?',(pid,g.user['organization_id'])).fetchone()
def integer(raw,label,maximum=2000000000):
 try:v=int(str(raw).strip())
 except (ValueError,TypeError):raise ValueError(f'{label} must be a whole number.')
 if str(raw).strip() not in (str(v),f'+{v}') or v<0 or v>maximum:raise ValueError(f'{label} must be between 0 and {maximum}.')
 return v
def price(raw,label):
 if not (raw or '').strip():return None
 try:v=Decimal(raw)
 except InvalidOperation:raise ValueError(f'{label} must be a valid number.')
 if not v.is_finite() or v<0 or v>Decimal('999999999999'):raise ValueError(f'{label} must be non-negative.')
 return str(v.quantize(Decimal('.01')))
@app.route('/')
def index():return redirect(url_for('dashboard') if g.user else url_for('login'))
@app.route('/signup',methods=['GET','POST'])
def signup():
 if g.user:return redirect(url_for('dashboard'))
 if request.method=='POST':
  email=request.form.get('email','').strip().lower();pw=request.form.get('password','');confirm=request.form.get('confirm_password','');name=' '.join(request.form.get('organization_name','').split())
  name_err=organization_name_error(name)
  err=('Enter a valid email address.' if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) or len(email)>254 else password_error(pw) if password_error(pw) else 'Passwords do not match.' if pw!=confirm else name_err)
  if err:flash(err,'error')
  else:
   try:
    with g.db:
     oid=g.db.execute('INSERT INTO organizations(name,created_at) VALUES(?,?)',(name,now())).lastrowid
     g.db.execute('INSERT INTO users(organization_id,email,password_hash,created_at) VALUES(?,?,?,?)',(oid,email,generate_password_hash(pw,method='scrypt'),now()))
    uid=g.db.execute('SELECT id FROM users WHERE email=? COLLATE NOCASE',(email,)).fetchone()['id'];session.clear();session['user_id']=uid;session['_csrf']=secrets.token_urlsafe(32);flash('Workspace created. Welcome to StockFlow!','success');return redirect(url_for('dashboard'))
   except sqlite3.IntegrityError:flash('An account with this email already exists.','error')
 return render_template('auth.html',mode='signup')
@app.route('/login',methods=['GET','POST'])
def login():
 if g.user:return redirect(url_for('dashboard'))
 if request.method=='POST':
  u=g.db.execute('SELECT id,password_hash FROM users WHERE email=? COLLATE NOCASE',(request.form.get('email','').strip().lower(),)).fetchone()
  if not u or not check_password_hash(u['password_hash'],request.form.get('password','')):flash('Email or password is incorrect.','error')
  else:session.clear();session['user_id']=u['id'];session['_csrf']=secrets.token_urlsafe(32);flash('Signed in successfully.','success');return redirect(url_for('dashboard'))
 return render_template('auth.html',mode='login')
@app.post('/logout')
@required
def logout():session.clear();flash('You have signed out.','success');return redirect(url_for('login'))
@app.route('/dashboard')
@required
def dashboard():
 oid=g.user['organization_id'];summary=g.db.execute("SELECT COUNT(*) product_count,COALESCE(SUM(quantity),0) total_units,COALESCE(SUM(quantity*CAST(COALESCE(cost_price,'0') AS REAL)),0) inventory_cost FROM products WHERE organization_id=?",(oid,)).fetchone();low=g.db.execute('SELECT * FROM products WHERE organization_id=? AND quantity<=COALESCE(low_stock_threshold,?) ORDER BY quantity,name',(oid,g.user['default_threshold'])).fetchall();recent=g.db.execute('SELECT * FROM products WHERE organization_id=? ORDER BY updated_at DESC LIMIT 5',(oid,)).fetchall();return render_template('dashboard.html',summary=summary,low=low,recent=recent)
@app.route('/products')
@required
def products():
 q=request.args.get('q','').strip()[:120];status=request.args.get('status','all');sql='SELECT * FROM products WHERE organization_id=?';args=[g.user['organization_id']]
 if q:
  esc=q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_');sql+=" AND (name LIKE ? ESCAPE '\\' OR sku LIKE ? ESCAPE '\\')";args += [f'%{esc}%',f'%{esc}%']
 if status=='low':sql+=' AND quantity<=COALESCE(low_stock_threshold,?)';args.append(g.user['default_threshold'])
 elif status=='out':sql+=' AND quantity=0'
 elif status=='healthy':sql+=' AND quantity>COALESCE(low_stock_threshold,?)';args.append(g.user['default_threshold'])
 rows=g.db.execute(sql+' ORDER BY updated_at DESC,id DESC',args).fetchall();return render_template('products.html',products=rows,q=q,status=status)
@app.route('/products/new',methods=['GET','POST'])
@required
def product_new():return product_form(None)
@app.route('/products/<int:pid>/edit',methods=['GET','POST'])
@required
def product_edit(pid):
 p=owned(pid)
 if not p:abort(404)
 return product_form(p)
def product_form(p):
 if request.method=='POST':
  name=request.form.get('name','').strip();sku=request.form.get('sku','').strip();desc=request.form.get('description','').strip()
  try:
   if not name or len(name)>120:raise ValueError('Product name is required (max 120 characters).')
   if not sku or len(sku)>64:raise ValueError('SKU is required (max 64 characters).')
   if len(desc)>1000:raise ValueError('Description must be at most 1000 characters.')
   qty=integer(request.form.get('quantity'),'Quantity');cost=price(request.form.get('cost_price'),'Cost price');selling=price(request.form.get('selling_price'),'Selling price');raw=request.form.get('low_stock_threshold','').strip();th=integer(raw,'Low-stock threshold') if raw else None;stamp=now();oid=g.user['organization_id']
   if p:g.db.execute('UPDATE products SET name=?,sku=?,description=?,quantity=?,cost_price=?,selling_price=?,low_stock_threshold=?,updated_at=? WHERE id=? AND organization_id=?',(name,sku,desc,qty,cost,selling,th,stamp,p['id'],oid))
   else:g.db.execute('INSERT INTO products(organization_id,name,sku,description,quantity,cost_price,selling_price,low_stock_threshold,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(oid,name,sku,desc,qty,cost,selling,th,stamp,stamp))
   g.db.commit();flash('Product saved successfully.','success');return redirect(url_for('products'))
  except ValueError as e:flash(str(e),'error')
  except sqlite3.IntegrityError:g.db.rollback();flash('That SKU is already used in your workspace.','error')
 return render_template('product_form.html',product=p)
@app.post('/products/<int:pid>/delete')
@required
def product_delete(pid):
 if not owned(pid):abort(404)
 g.db.execute('DELETE FROM products WHERE id=? AND organization_id=?',(pid,g.user['organization_id']));g.db.commit();flash('Product deleted.','success');return redirect(url_for('products'))
@app.route('/settings',methods=['GET','POST'])
@required
def settings():
 if request.method=='POST':
  try:
   threshold=integer(request.form.get('default_threshold'),'Default threshold');name=' '.join(request.form.get('organization_name','').split())
   name_err=organization_name_error(name)
   if name_err:raise ValueError(name_err)
   g.db.execute('UPDATE organizations SET name=?,default_threshold=? WHERE id=?',(name,threshold,g.user['organization_id']));g.db.commit();flash('Settings saved.','success');return redirect(url_for('settings'))
  except ValueError as e:flash(str(e),'error')
 org=g.db.execute('SELECT * FROM organizations WHERE id=?',(g.user['organization_id'],)).fetchone();return render_template('settings.html',org=org)
@app.errorhandler(400)
def bad(e):return render_template('error.html',code=400,message=getattr(e,'description','Bad request')),400
@app.errorhandler(404)
def missing(e):return render_template('error.html',code=404,message='This page or product was not found.'),404
with app.app_context():init_db()
if __name__=='__main__':app.run(host='127.0.0.1',port=int(os.environ.get('PORT','5000')),debug=False)
