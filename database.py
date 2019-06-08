from sqlalchemy import Column, DateTime, String, Integer, ForeignKey, func,Boolean
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

Base = declarative_base()
engine = create_engine('sqlite:///newtiebar.sqlite')


# 贴吧
class Bar(Base):
    __tablename__ = 'bar'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    kind = Column(String)
    hassend = Column(Boolean)


# # 代理
class Proxy(Base):
    __tablename__ = 'proxy'
    id = Column(Integer, primary_key=True)
    ip = Column(String)
    occupy = Column(Boolean)



# 帖子
class Tie(Base):
    __tablename__ = 'tie'
    id = Column(Integer, primary_key=True)
    url = Column(String)
    tid = Column(String)
    bar_name = Column(String)
#
#
# # 客户
class Customer(Base):
    __tablename__ = 'customer'
    id = Column(Integer, primary_key=True)
    nick_name = Column(String)
    url = Column(String)
    has_send = Column(Boolean)
#
#
# class User(Base):
#     __tablename__ = 'user'
#     id = Column(Integer, primary_key=True)
#     cookie = Column(String)
#     bduss = Column(String)
#     occupy = Column(Boolean)
#
#
# # 代理与user匹配表
# class ReplyUser(Base):
#     __tablename__ = 'replyuser'
#     id = Column(Integer, primary_key=True)
#     user_id = Column(String)
#     proxy_id = Column(String)
#
#
# # 已经回复的帖子
# class Reply(Base):
#     __tablename__ = 'reply'
#     id = Column(Integer, primary_key=True)
#     tid = Column(String)
#     times = Column(Integer)


Base.metadata.create_all(engine)
