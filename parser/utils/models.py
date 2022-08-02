from pathlib import Path

from pydantic import BaseModel, validator


class Person(BaseModel):
    raw_name: str = ''
    lemm_name: str = ''
    gender:str = ''
    fio: dict = {}

    @validator('raw_name', pre=True)
    def pre_prep(cls, v):
        return ' '.join(v.split())

class AppoitmentLine(BaseModel):
    raw_line: str|None = ''
    appointees: list[Person] = [] # список людей, которых назначили 
    resignees: list[Person] = []
    position: str|None = ''


class FileData(BaseModel):
    doc_id:str=None
    file_name : str = None
    file_path : str|Path = None
    date : str = None
    text_raw : str|None = None
    splitted_text:list[str]=None
    url : str = None
    appointment_lines: list[AppoitmentLine] = [] # events
    author:str = None # кто подписал
    naznach_line:str = None
    

