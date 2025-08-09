-- 云推客严选数据库初始化脚本
-- 创建所有核心数据表和索引
-- Author: 云推客严选开发团队
-- Date: 2024

-- 启用UUID扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wechat_openid VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    nickname VARCHAR(100) NOT NULL,
    avatar_url TEXT,
    role VARCHAR(20) NOT NULL CHECK (role IN ('merchant', 'leader', 'influencer')),
    profile_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建用户表索引
CREATE INDEX IF NOT EXISTS idx_users_wechat_openid ON users(wechat_openid);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);

-- 创建商品表
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    merchant_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    commission_rate DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    category VARCHAR(50),
    sku_data JSONB DEFAULT '{}',
    analytics_data JSONB DEFAULT '{}',
    platform VARCHAR(20) DEFAULT 'wechat' CHECK (platform IN ('wechat', 'douyin', 'kuaishou')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'deleted')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建商品表索引
CREATE INDEX IF NOT EXISTS idx_products_merchant_id ON products(merchant_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_platform ON products(platform);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_commission_rate ON products(commission_rate DESC);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at DESC);

-- 创建订单表
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_no VARCHAR(50) UNIQUE NOT NULL,
    buyer_id UUID REFERENCES users(id),
    influencer_id UUID REFERENCES users(id),
    leader_id UUID REFERENCES users(id),
    total_amount DECIMAL(10,2) NOT NULL,
    commission_amount DECIMAL(10,2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'shipped', 'completed', 'cancelled', 'refunded')),
    platform VARCHAR(20) DEFAULT 'wechat',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建订单表索引
CREATE INDEX IF NOT EXISTS idx_orders_order_no ON orders(order_no);
CREATE INDEX IF NOT EXISTS idx_orders_buyer_id ON orders(buyer_id);
CREATE INDEX IF NOT EXISTS idx_orders_influencer_id ON orders(influencer_id);
CREATE INDEX IF NOT EXISTS idx_orders_leader_id ON orders(leader_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_platform ON orders(platform);

-- 创建订单项表
CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    commission DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建订单项表索引
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);

-- 创建货盘表
CREATE TABLE IF NOT EXISTS collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    leader_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    settings JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'deleted')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建货盘表索引
CREATE INDEX IF NOT EXISTS idx_collections_leader_id ON collections(leader_id);
CREATE INDEX IF NOT EXISTS idx_collections_status ON collections(status);
CREATE INDEX IF NOT EXISTS idx_collections_created_at ON collections(created_at DESC);

-- 创建货盘商品表
CREATE TABLE IF NOT EXISTS collection_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    sort_order INTEGER DEFAULT 0,
    recommendation_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建货盘商品表索引
CREATE INDEX IF NOT EXISTS idx_collection_items_collection_id ON collection_items(collection_id);
CREATE INDEX IF NOT EXISTS idx_collection_items_product_id ON collection_items(product_id);
CREATE INDEX IF NOT EXISTS idx_collection_items_sort_order ON collection_items(sort_order);

-- 创建申样请求表
CREATE TABLE IF NOT EXISTS sample_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    requester_id UUID REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    target_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'completed')),
    response_note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建申样请求表索引
CREATE INDEX IF NOT EXISTS idx_sample_requests_requester_id ON sample_requests(requester_id);
CREATE INDEX IF NOT EXISTS idx_sample_requests_product_id ON sample_requests(product_id);
CREATE INDEX IF NOT EXISTS idx_sample_requests_target_user_id ON sample_requests(target_user_id);
CREATE INDEX IF NOT EXISTS idx_sample_requests_status ON sample_requests(status);
CREATE INDEX IF NOT EXISTS idx_sample_requests_created_at ON sample_requests(created_at DESC);

-- 创建用户关系表
CREATE TABLE IF NOT EXISTS user_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    leader_id UUID REFERENCES users(id) ON DELETE CASCADE,
    influencer_id UUID REFERENCES users(id) ON DELETE CASCADE,
    invite_code VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'deleted')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(leader_id, influencer_id)
);

-- 创建用户关系表索引
CREATE INDEX IF NOT EXISTS idx_user_relationships_leader_id ON user_relationships(leader_id);
CREATE INDEX IF NOT EXISTS idx_user_relationships_influencer_id ON user_relationships(influencer_id);
CREATE INDEX IF NOT EXISTS idx_user_relationships_invite_code ON user_relationships(invite_code);
CREATE INDEX IF NOT EXISTS idx_user_relationships_status ON user_relationships(status);

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要的表添加更新时间触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_collections_updated_at BEFORE UPDATE ON collections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sample_requests_updated_at BEFORE UPDATE ON sample_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 启用行级安全策略
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE sample_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_relationships ENABLE ROW LEVEL SECURITY;

-- 设置基础权限
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- 创建基础的行级安全策略（示例）
-- 用户只能查看和修改自己的数据
CREATE POLICY "Users can view own data" ON users
    FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "Users can update own data" ON users
    FOR UPDATE USING (auth.uid()::text = id::text);

-- 商品策略：商家可以管理自己的商品，其他用户可以查看
CREATE POLICY "Merchants can manage own products" ON products
    FOR ALL USING (auth.uid()::text = merchant_id::text);

CREATE POLICY "All users can view active products" ON products
    FOR SELECT USING (status = 'active');

-- 订单策略：用户可以查看相关的订单
CREATE POLICY "Users can view related orders" ON orders
    FOR SELECT USING (
        auth.uid()::text = buyer_id::text OR 
        auth.uid()::text = influencer_id::text OR 
        auth.uid()::text = leader_id::text
    );

-- 插入测试数据
INSERT INTO users (wechat_openid, nickname, role, profile_data) VALUES
('test_merchant_001', '测试商家', 'merchant', '{"company": "测试公司", "verified": true}'),
('test_leader_001', '测试团长', 'leader', '{"team_name": "精选团队", "wechat_id": "leader001"}'),
('test_influencer_001', '测试达人', 'influencer', '{"fans_count": 10000, "category": "美妆"}')
ON CONFLICT (wechat_openid) DO NOTHING;

-- 插入测试商品数据
INSERT INTO products (merchant_id, title, description, price, commission_rate, category, platform)
SELECT 
    u.id,
    '测试商品' || generate_series(1, 5),
    '这是一个测试商品的详细描述',
    (random() * 1000 + 10)::decimal(10,2),
    (random() * 0.3 + 0.05)::decimal(5,2),
    CASE (random() * 3)::int 
        WHEN 0 THEN '美妆护肤'
        WHEN 1 THEN '服装配饰'
        ELSE '数码家电'
    END,
    CASE (random() * 3)::int
        WHEN 0 THEN 'wechat'
        WHEN 1 THEN 'douyin'
        ELSE 'kuaishou'
    END
FROM users u 
WHERE u.role = 'merchant'
LIMIT 1;

COMMIT;