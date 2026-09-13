-- Metohub Multi-Tenant E-Commerce Database Schema (Python FastAPI)
CREATE DATABASE IF NOT EXISTS `glov_py` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `glov_py`;

CREATE TABLE IF NOT EXISTS `plans` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL UNIQUE,
    `slug` VARCHAR(50) NOT NULL UNIQUE,
    `price_weekly` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `week_count` INT NOT NULL DEFAULT 52,
    `trial_days` INT NOT NULL DEFAULT 90,
    `banner_limit` INT NOT NULL DEFAULT 0,
    `price_monthly` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `product_limit` INT NOT NULL DEFAULT 50,
    `description` VARCHAR(255) NULL,
    `features_json` TEXT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `plans` (`id`, `name`, `slug`, `price_weekly`, `week_count`, `trial_days`, `banner_limit`, `price_monthly`, `product_limit`, `description`, `features_json`)
VALUES
(1, 'Base', 'base', 49.00, 52, 90, 0, 212.33, 100, 'Essential entry-level store for solo merchants and boutique starters.', '["3 Months Free Trial Included", "Up to 100 Active Products", "Standard Storefront & Branded Sub-URL", "Customize the Theme", "Standard Shopping Cart & Checkout", "Direct UPI Payment Supported", "Order Management & Email Receipts", "Standard Support"]'),
(2, 'Essential', 'essential', 60.00, 52, 90, 3, 260.00, 250, 'Growth tier for expanding stores needing higher volume and rental flexibility.', '["3 Months Free Trial Included", "Up to 250 Active Products", "Dual Retail & Rental Engine (Daily / Weekend)", "Security Deposit & Date Picker Support", "Custom Storefront Colors & Theme Engine", "UPI QR Code Upload & Screenshot Verification", "Stock Inventory & Out-of-Stock Alerts", "Priority Support Response"]'),
(3, 'Pro', 'pro', 69.00, 52, 90, 9, 299.00, -1, 'Enterprise-grade power for high-volume merchants needing unlimited scale.', '["3 Months Free Trial Included", "Unlimited Active Products", "All Essential Tier Features Included", "Full 16-Token Custom Theme Styling", "Advanced Product Views & Sales Analytics", "Custom Hero Banners & Promo Banners", "Fast-Track Order Processing & Status Tracking", "Dedicated 24/7 Account Support"]')
ON DUPLICATE KEY UPDATE
    `price_weekly`=VALUES(`price_weekly`),
    `week_count`=VALUES(`week_count`),
    `trial_days`=VALUES(`trial_days`),
    `banner_limit`=VALUES(`banner_limit`),
    `price_monthly`=VALUES(`price_monthly`),
    `product_limit`=VALUES(`product_limit`),
    `description`=VALUES(`description`),
    `features_json`=VALUES(`features_json`);

CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(150) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `phone` VARCHAR(50) NULL,
    `whatsapp` VARCHAR(50) NULL,
    `country` VARCHAR(100) NULL,
    `address` TEXT NULL,
    `national_id_number` VARCHAR(100) NULL,
    `role` ENUM('admin', 'seller', 'customer') NOT NULL DEFAULT 'seller',
    `status` ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `tenants` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `plan_id` INT NOT NULL,
    `name` VARCHAR(120) NOT NULL,
    `slug` VARCHAR(100) NOT NULL UNIQUE,
    `business_type` VARCHAR(80) NOT NULL,
    `tagline` VARCHAR(255) NULL,
    `description` TEXT NULL,
    `logo` VARCHAR(255) NULL,
    `logo_webp` VARCHAR(255) NULL,
    `banner` VARCHAR(255) NULL,
    `banner_webp` VARCHAR(255) NULL,
    `currency` VARCHAR(10) NOT NULL DEFAULT '₹',
    `currency_symbol` VARCHAR(5) NOT NULL DEFAULT '₹',
    `theme_color` VARCHAR(20) NOT NULL DEFAULT '#6366f1',
    `theme_settings` TEXT NULL,
    `contact_email` VARCHAR(150) NULL,
    `contact_phone` VARCHAR(50) NULL,
    `address` TEXT NULL,
    `hide_default_banner` TINYINT(1) NOT NULL DEFAULT 0,
    `enable_upi` TINYINT(1) NOT NULL DEFAULT 1,
    `enable_cod` TINYINT(1) NOT NULL DEFAULT 0,
    `enable_bank` TINYINT(1) NOT NULL DEFAULT 0,
    `enable_card` TINYINT(1) NOT NULL DEFAULT 0,
    `upi_id` VARCHAR(150) NULL,
    `upi_qr_image` VARCHAR(255) NULL,
    `bank_details` TEXT NULL,
    `subscription_proof` VARCHAR(255) NULL,
    `subscription_transaction_id` VARCHAR(120) NULL,
    `trial_start` TIMESTAMP NULL,
    `trial_end` TIMESTAMP NULL,
    `subscription_start` TIMESTAMP NULL,
    `subscription_end` TIMESTAMP NULL,
    `status` ENUM('active', 'suspended', 'pending') NOT NULL DEFAULT 'active',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`plan_id`) REFERENCES `plans`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `tenant_banners` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `tenant_id` INT NOT NULL,
    `image_path` VARCHAR(255) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `categories` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `tenant_id` INT NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `slug` VARCHAR(100) NOT NULL,
    `description` VARCHAR(255) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `unique_tenant_category` (`tenant_id`, `slug`),
    FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `products` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `tenant_id` INT NOT NULL,
    `category_id` INT NULL,
    `name` VARCHAR(150) NOT NULL,
    `slug` VARCHAR(150) NOT NULL,
    `sku` VARCHAR(50) NULL,
    `description` TEXT NULL,
    `price` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `is_rental` TINYINT(1) NOT NULL DEFAULT 0,
    `rental_period` ENUM('none', 'per_day', 'per_weekend', 'per_month') NOT NULL DEFAULT 'none',
    `rental_price_daily` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `rental_price_weekend` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `rental_deposit` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `stock_quantity` INT NOT NULL DEFAULT 10,
    `featured_image_webp` VARCHAR(255) NULL,
    `views_count` INT NOT NULL DEFAULT 0,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `unique_tenant_product` (`tenant_id`, `slug`),
    FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`category_id`) REFERENCES `categories`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `product_images` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `product_id` INT NOT NULL,
    `tenant_id` INT NULL,
    `image_path` VARCHAR(255) NULL,
    `image_path_webp` VARCHAR(255) NULL,
    `is_primary` TINYINT(1) NOT NULL DEFAULT 1,
    `display_order` INT NOT NULL DEFAULT 0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`product_id`) REFERENCES `products`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `orders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `tenant_id` INT NOT NULL,
    `order_number` VARCHAR(30) NOT NULL UNIQUE,
    `customer_name` VARCHAR(100) NOT NULL,
    `customer_email` VARCHAR(150) NOT NULL,
    `customer_phone` VARCHAR(50) NOT NULL,
    `shipping_address` TEXT NOT NULL,
    `city` VARCHAR(100) NULL,
    `postal_code` VARCHAR(20) NULL,
    `total_amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `payment_method` VARCHAR(50) NOT NULL DEFAULT 'cod',
    `payment_status` ENUM('pending', 'paid', 'refunded') NOT NULL DEFAULT 'pending',
    `payment_proof` VARCHAR(255) NULL,
    `transaction_ref` VARCHAR(120) NULL,
    `is_rental_order` TINYINT(1) NOT NULL DEFAULT 0,
    `rental_duration_days` INT NOT NULL DEFAULT 1,
    `rental_start_date` DATE NULL,
    `status` ENUM('pending', 'processing', 'completed', 'cancelled') NOT NULL DEFAULT 'pending',
    `notes` TEXT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `order_items` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `order_id` INT NOT NULL,
    `tenant_id` INT NOT NULL,
    `product_id` INT NULL,
    `product_name` VARCHAR(150) NOT NULL,
    `quantity` INT NOT NULL DEFAULT 1,
    `unit_price` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `is_rental` TINYINT(1) NOT NULL DEFAULT 0,
    `rental_type` VARCHAR(30) NULL,
    `rental_start_date` DATE NULL,
    `rental_days` INT NULL,
    `line_total` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `total_price` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    FOREIGN KEY (`order_id`) REFERENCES `orders`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`product_id`) REFERENCES `products`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `pages` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `slug` VARCHAR(50) NOT NULL UNIQUE,
    `title` VARCHAR(100) NOT NULL,
    `content` TEXT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO `pages` (`slug`, `title`, `content`) VALUES 
('terms', 'Terms of Use', 'By using Metohub, you agree to our standard terms of use. You will not sell illegal or prohibited items, and you agree to maintain your store in good standing.');
