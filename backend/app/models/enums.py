from __future__ import annotations

import enum


class OrganizationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"


class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    SECURITY_ANALYST = "SECURITY_ANALYST"
    MEMBER = "MEMBER"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INVITED = "INVITED"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"


class AgentType(str, enum.Enum):
    GENERAL = "GENERAL"
    CODING = "CODING"
    DATA = "DATA"
    SECURITY = "SECURITY"
    AUTOMATION = "AUTOMATION"
    CUSTOM = "CUSTOM"


class AgentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    SUSPENDED = "SUSPENDED"


class AgentRiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionType(str, enum.Enum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"
    NETWORK = "NETWORK"
    TRANSFER = "TRANSFER"
    ADMIN = "ADMIN"


class Environment(str, enum.Enum):
    DEVELOPMENT = "DEVELOPMENT"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"


class DataSensitivity(str, enum.Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class PrivilegeLevel(str, enum.Enum):
    LOW = "LOW"
    STANDARD = "STANDARD"
    ELEVATED = "ELEVATED"
    ADMIN = "ADMIN"
