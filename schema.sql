CREATE TABLE IF NOT EXISTS brands (
    id INT NOT NULL,
    brand_name VARCHAR(255) NOT NULL,
    manufacturer VARCHAR(255) NOT NULL,
    price_inr DECIMAL(10,2) NOT NULL,
    is_jan_aushadhi TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uk_brands_name (brand_name),
    KEY idx_brands_price (price_inr)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS salts (
    id INT NOT NULL,
    salt_name VARCHAR(255) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_salts_name (salt_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS brand_salts (
    brand_id INT NOT NULL,
    salt_id INT NOT NULL,
    strength_mg DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (brand_id, salt_id, strength_mg),
    KEY idx_brand_salts_brand (brand_id),
    KEY idx_brand_salts_salt_strength (salt_id, strength_mg),
    CONSTRAINT fk_bs_brand FOREIGN KEY (brand_id) REFERENCES brands(id),
    CONSTRAINT fk_bs_salt FOREIGN KEY (salt_id) REFERENCES salts(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
