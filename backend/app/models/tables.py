from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from ..database import Base

# Many-to-many association tables for user permissions and features
user_permissions = Table(
    'user_permissions', 
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True),
    Column('granted_at', DateTime, default=func.now())
)

user_features = Table(
    'user_features', 
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('feature_id', Integer, ForeignKey('features.id'), primary_key=True),
    Column('granted_at', DateTime, default=func.now())
)

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True),
    Column('granted_at', DateTime, default=func.now())
)

role_features = Table(
    'role_features',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True), 
    Column('feature_id', Integer, ForeignKey('features.id'), primary_key=True),
    Column('granted_at', DateTime, default=func.now())
)

# Group permissions and features association tables
group_permissions = Table(
    'group_permissions',
    Base.metadata,
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True),
    Column('granted_at', DateTime, default=func.now())
)

group_features = Table(
    'group_features',
    Base.metadata,
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True),
    Column('feature_id', Integer, ForeignKey('features.id'), primary_key=True),
    Column('granted_at', DateTime, default=func.now())
) 