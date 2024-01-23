# Website2 
Sequence Input Server

# Requirements :
Install MySQL installer latest version
Install python 3.11.5
Install ngrok 
### Windows 
Set up the flask environment
```bash
  pip install flask
  pip3 install pipenv
  pipenv shell
  pipenv install flask
  pipenv shell
  pip install mysql-connector-python 
```

```bash
cd .virtualenvs\<your_env>
or
pipenv shell
```
```bash
cd <your_directory>
set FLASK_APP=app.py
set FLASK_ENV=development
set FLASK_RUN_HOST=127.0.0.1
set FLASK_RUN_PORT=5000
flask run
```
### Script files :
`app.py`
`index.html`
`user_files.html`
`all_files.html`

# Connection string to database 
### edit the string accordingly in app.py 
    db_config: dict = {
    'host': 'localhost',
    'user': 'root',
    'password': 'divya',
    'database': 'mydb'
}
### other files related to database: 
`mydb-website2db.mwb` 
## Ngrok 
```bash
Account details:
email: testdivya368@gmail.com
password : 
```
#### Usage :
Using visual studio code or any other compatible software

