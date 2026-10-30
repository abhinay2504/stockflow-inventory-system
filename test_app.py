import os,tempfile,unittest
from contextlib import closing
import app as module
from app import app,init_db
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=module.DB_PATH;module.DB_PATH=os.path.join(self.tmp.name,'test.db');app.config.update(TESTING=True,SECRET_KEY='tests');init_db();self.c=app.test_client()
 def tearDown(self):module.DB_PATH=self.old;self.tmp.cleanup()
 def token(self,c=None):
  with (c or self.c).session_transaction() as s:return s.get('_csrf','')
 def signup(self,c,email,org):
  c.get('/signup');return c.post('/signup',data={'_csrf':self.token(c),'email':email,'password':'StrongPass123!','confirm_password':'StrongPass123!','organization_name':org},follow_redirects=True)
 def add(self,c,name='Widget',sku='W-1',qty='3'):
  c.get('/products/new');return c.post('/products/new',data={'_csrf':self.token(c),'name':name,'sku':sku,'quantity':qty,'cost_price':'10.50','selling_price':'15.00'},follow_redirects=True)
 def test_password_policy_rejects_missing_character_classes(self):
  cases=[('lowercase123!','capital letter'),('UPPERCASE123!','lowercase letter'),('StrongPass!!!','number'),('StrongPass123','special character'),('Ab1!','8 and 128')]
  for password,expected in cases:
   with self.subTest(password=password):
    self.c.get('/signup')
    r=self.c.post('/signup',data={'_csrf':self.token(),'email':'policy@example.com','password':password,'confirm_password':password,'organization_name':'Policy Shop'},follow_redirects=True)
    self.assertIn(expected.encode(),r.data.lower())
    with closing(module.connect_db()) as d:self.assertEqual(d.execute('select count(*) from users').fetchone()[0],0)
 def test_password_policy_accepts_strong_password(self):
  r=self.signup(self.c,'strong@example.com','Strong Shop')
  self.assertEqual(r.status_code,200)
  with closing(module.connect_db()) as d:self.assertEqual(d.execute('select count(*) from users').fetchone()[0],1)
 def test_signup_hash_login(self):
  r=self.signup(self.c,'one@example.com','One Shop');self.assertEqual(r.status_code,200);self.assertIn(b'Total products',self.c.get('/dashboard').data)
  with closing(module.connect_db()) as d:self.assertNotEqual(d.execute('select password_hash from users').fetchone()[0],'StrongPass123!')
 def test_crud_low_stock_settings(self):
  self.signup(self.c,'one@example.com','One Shop');self.add(self.c);page=self.c.get('/dashboard').data;self.assertIn(b'Widget',page);self.assertIn(b'3 left',page);self.assertIn(b'Low stock',page);self.assertIn(b'Widget',self.c.get('/products?q=W-1').data)
  r=self.c.post('/settings',data={'_csrf':self.token(),'organization_name':'One Shop','default_threshold':'2'},follow_redirects=True);self.assertEqual(r.status_code,200)
  self.c.get('/products/new');r=self.c.post('/products/new',data={'_csrf':self.token(),'name':'Second','sku':'W-1','quantity':'1'},follow_redirects=True);self.assertIn(b'already used',r.data.lower())
 def test_tenant_isolation(self):
  self.signup(self.c,'one@example.com','One Shop');self.add(self.c,'Private Widget','SECRET-SKU','8');other=app.test_client();self.signup(other,'two@example.com','Two Shop');self.assertNotIn(b'Private Widget',other.get('/products').data);self.assertEqual(other.get('/products/1/edit').status_code,404);self.assertEqual(other.post('/products/1/delete',data={'_csrf':self.token(other)}).status_code,404)
 def test_csrf_and_validation(self):
  self.signup(self.c,'one@example.com','One Shop');self.assertEqual(self.c.post('/products/new',data={'name':'x','sku':'x','quantity':'1'}).status_code,400);self.c.get('/products/new');r=self.c.post('/products/new',data={'_csrf':self.token(),'name':'x','sku':'x','quantity':'-1'},follow_redirects=True);self.assertIn(b'quantity must be between 0 and 2000000000',r.data.lower())
 def test_logout(self):
  self.signup(self.c,'one@example.com','One Shop');self.c.post('/logout',data={'_csrf':self.token()},follow_redirects=True);self.assertEqual(self.c.get('/dashboard').status_code,302)
 def test_organization_name_validation_on_signup(self):
  cases=[('', 'between 2 and 80'),('   ', 'between 2 and 80'),('A', 'between 2 and 80'),('!!!', 'letter or number'),('X'*81, 'between 2 and 80'),('Shop\x01Name', 'control characters')]
  for name,expected in cases:
   with self.subTest(name=repr(name)):
    self.c.get('/signup')
    r=self.c.post('/signup',data={'_csrf':self.token(),'email':'orgcheck@example.com','password':'StrongPass123!','confirm_password':'StrongPass123!','organization_name':name},follow_redirects=True)
    self.assertIn(expected.encode(),r.data.lower())
    with closing(module.connect_db()) as d:self.assertEqual(d.execute('select count(*) from users').fetchone()[0],0)
 def test_organization_name_normalization_and_international_names(self):
  r=self.signup(self.c,'intl@example.com','  Café   Store  ')
  self.assertEqual(r.status_code,200)
  with closing(module.connect_db()) as d:org=d.execute('select name from organizations').fetchone()['name']
  self.assertEqual(org,'Café Store')
 def test_organization_name_validation_in_settings(self):
  self.signup(self.c,'settings@example.com','Good Store')
  r=self.c.post('/settings',data={'_csrf':self.token(),'organization_name':'!!!','default_threshold':'5'},follow_redirects=True)
  self.assertIn(b'letter or number',r.data.lower())
  with closing(module.connect_db()) as d:self.assertEqual(d.execute('select name from organizations').fetchone()['name'],'Good Store')
if __name__=='__main__':unittest.main(verbosity=2)
