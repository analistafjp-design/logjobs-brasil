from fastapi import FastAPI
app=FastAPI(title='LogJobs Brasil')

@app.get('/')
def root():
    return {'status':'online'}
