from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float, func
from sqlalchemy.orm import relationship
from app.db_clean import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, index=True, nullable=False)
    password = Column(String(256), nullable=False) # Note: sqlite uses 'password', not 'hashed_password' in the schema provided
    name = Column(String(255), nullable=False)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    avatar = Column(String(1024), nullable=True)
    theme = Column(String(32), default="dark")
    role = Column(String(64), default="user")
    google_token = Column(Text, nullable=True)
    google_email = Column(String(320), nullable=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    manager = relationship("User", remote_side=[id], backref="employees")
    workspaces = relationship("Workspace", back_populates="user")
    workflows = relationship("Workflow", back_populates="user")
    products = relationship("Product", back_populates="creator")
    customers = relationship("Customer", back_populates="creator")
    wallet = relationship("Wallet", uselist=False, back_populates="user")
    manager_subscription = relationship("ManagerSubscription", uselist=False, back_populates="user")


class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(64), nullable=False)
    description = Column(Text)
    settings = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="workspaces")
    items = relationship("Item", back_populates="workspace")
    scenarios = relationship("Scenario", back_populates="workspace")


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(64), default="task")
    status = Column(String(64), default="todo")
    priority = Column(String(64), default="medium")
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    parent_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    meta_data = Column('metadata', Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    workspace = relationship("Workspace", back_populates="items")
    assignee = relationship("User", foreign_keys=[assignee_id])
    children = relationship("Item", remote_side=[parent_id])


class Scenario(Base):
    __tablename__ = "scenarios"
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    steps = Column(Text)
    conditions = Column(Text)
    status = Column(String(64), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship("Workspace", back_populates="scenarios")


class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, index=True)
    from_workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    to_workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    channel_type = Column(String(64), nullable=False)
    config = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserPermission(Base):
    __tablename__ = "user_permissions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission_type = Column(String(64), nullable=False)
    granted_by = Column(Integer, ForeignKey("users.id"))
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked = Column(Boolean, default=False)


class SystemSetting(Base):
    __tablename__ = "system_settings"
    key = Column(String(255), primary_key=True)
    value = Column(Text)
    group_name = Column(String(64))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(255), nullable=False)
    details = Column(Text)
    ip_address = Column(String(64))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    data = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="workflows")


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(64))
    email = Column(String(255))
    address = Column(Text)
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator = relationship("User", back_populates="customers")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(255))
    unit = Column(String(64), default="cái")
    price = Column(Float, default=0)
    stock_quantity = Column(Integer, default=0)
    description = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator = relationship("User", back_populates="products")


class ImportTransaction(Base):
    __tablename__ = "import_transactions"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, nullable=False)
    supplier_name = Column(String(255))
    total_amount = Column(Float, default=0)
    notes = Column(Text)
    status = Column(String(64), default="completed")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    details = relationship("ImportDetail", back_populates="transaction")


class ImportDetail(Base):
    __tablename__ = "import_details"
    id = Column(Integer, primary_key=True, index=True)
    import_id = Column(Integer, ForeignKey("import_transactions.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    transaction = relationship("ImportTransaction", back_populates="details")
    product = relationship("Product")


class ExportTransaction(Base):
    __tablename__ = "export_transactions"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    total_amount = Column(Float, default=0)
    notes = Column(Text)
    status = Column(String(64), default="completed")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    details = relationship("ExportDetail", back_populates="transaction")


class ExportDetail(Base):
    __tablename__ = "export_details"
    id = Column(Integer, primary_key=True, index=True)
    export_id = Column(Integer, ForeignKey("export_transactions.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    transaction = relationship("ExportTransaction", back_populates="details")
    product = relationship("Product")


class SEAutomation(Base):
    __tablename__ = "se_automations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(64), nullable=False)
    config = Column(Text)
    enabled = Column(Boolean, default=True)
    last_run = Column(DateTime(timezone=True))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ScheduledReport(Base):
    __tablename__ = "scheduled_reports"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    report_type = Column(String(64), nullable=False)
    frequency = Column(String(64), nullable=False)
    channel = Column(String(64), nullable=False)
    recipients = Column(Text)
    status = Column(String(64), default="active")
    last_sent_at = Column(DateTime(timezone=True))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ManagerSubscription(Base):
    __tablename__ = "manager_subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    subscription_type = Column(String(64), nullable=False)
    amount = Column(Float, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(64), default="active")
    payment_method = Column(String(64))
    transaction_id = Column(String(255))
    auto_renew = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="manager_subscription")


class SubscriptionHistory(Base):
    __tablename__ = "subscription_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subscription_type = Column(String(64), nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime(timezone=True), server_default=func.now())
    payment_method = Column(String(64))
    transaction_id = Column(String(255))
    status = Column(String(64), default="completed")
    notes = Column(Text)


class Wallet(Base):
    __tablename__ = "wallets"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    balance = Column(Float, default=0)
    currency = Column(String(16), default="VND")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="wallet")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(16), default="VND")
    type = Column(String(64), nullable=False)
    status = Column(String(64), default="pending")
    method = Column(String(64))
    reference = Column(String(255))
    notes = Column(Text)
    meta_data = Column('metadata', Text)  # renamed attribute to avoid Declarative 'metadata' conflict
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
