CREATE DATABASE IF NOT EXISTS rental_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE rental_test;

CREATE TABLE IF NOT EXISTS car_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL UNIQUE,
    daily_rate DECIMAL(10,2) NOT NULL CHECK (daily_rate > 0),
    description TEXT
);
CREATE TABLE IF NOT EXISTS cars (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    brand VARCHAR(60) NOT NULL,
    model VARCHAR(60) NOT NULL,
    year SMALLINT NOT NULL,
    plate VARCHAR(12) NOT NULL UNIQUE,
    color VARCHAR(30) NOT NULL,
    mileage INT NOT NULL DEFAULT 0,
    status ENUM('available','rented','maintenance') NOT NULL DEFAULT 'available',
    CONSTRAINT fk_cars_category FOREIGN KEY (category_id) REFERENCES car_categories(id) ON DELETE RESTRICT,
    INDEX idx_cars_plate (plate)
);
CREATE TABLE IF NOT EXISTS clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    last_name VARCHAR(60) NOT NULL,
    first_name VARCHAR(60) NOT NULL,
    patronymic VARCHAR(60),
    passport VARCHAR(11) NOT NULL UNIQUE,
    driver_license VARCHAR(20) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(120),
    registered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_clients_passport (passport)
);
CREATE TABLE IF NOT EXISTS rentals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    car_id INT NOT NULL,
    client_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date_planned DATE NOT NULL,
    return_date DATE NULL,
    daily_rate DECIMAL(10,2) NOT NULL,
    total_cost DECIMAL(12,2) NOT NULL,
    status ENUM('active','closed','cancelled') NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_rentals_car FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE RESTRICT,
    CONSTRAINT fk_rentals_client FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT chk_rental_dates CHECK (end_date_planned >= start_date),
    INDEX idx_rentals_period (car_id, start_date, end_date_planned)
);

INSERT IGNORE INTO car_categories (id,name,daily_rate,description) VALUES
(1,'Эконом',1800,'Компактные автомобили для города'),(2,'Комфорт',3200,'Седаны среднего класса'),
(3,'Бизнес',5600,'Автомобили повышенного комфорта'),(4,'Внедорожник',4900,'Автомобили для поездок за город');
INSERT IGNORE INTO cars (id,category_id,brand,model,year,plate,color,mileage,status) VALUES
(1,1,'Lada','Granta',2021,'А123ВС69','Белый',42000,'available'),
(2,1,'Kia','Rio',2020,'В234ЕК69','Серебристый',51000,'available'),
(3,1,'Hyundai','Solaris',2022,'Е345КМ69','Синий',27000,'available'),
(4,2,'Toyota','Corolla',2021,'К456НО69','Белый',33000,'available'),
(5,2,'Skoda','Octavia',2023,'М567РТ69','Серый',18000,'available'),
(6,2,'Volkswagen','Jetta',2020,'Н678УХ69','Чёрный',46000,'available'),
(7,3,'BMW','3 Series',2022,'О789АВ69','Чёрный',22000,'available'),
(8,3,'Mercedes-Benz','C-Class',2021,'Р890СЕ69','Серебристый',31000,'available'),
(9,4,'Kia','Sportage',2023,'С901ТУ69','Синий',16000,'available'),
(10,4,'Toyota','RAV4',2022,'Т012ХА69','Белый',25000,'available');
INSERT IGNORE INTO clients (id,last_name,first_name,patronymic,passport,driver_license,phone,email) VALUES
(1,'Иванов','Иван','Иванович','6901 123456','6900123456','+79001234567','ivanov@example.ru'),
(2,'Петрова','Анна','Сергеевна','6902 234567','6901123456','+79011234567','petrova@example.ru'),
(3,'Сидоров','Павел','Олегович','6903 345678','6902123456','+79021234567','sidorov@example.ru'),
(4,'Кузнецова','Мария','Игоревна','6904 456789','6903123456','+79031234567','kuznetsova@example.ru'),
(5,'Смирнов','Дмитрий','Андреевич','6905 567890','6904123456','+79041234567','smirnov@example.ru'),
(6,'Попова','Елена','Викторовна','6906 678901','6905123456','+79051234567','popova@example.ru'),
(7,'Волков','Алексей','Романович','6907 789012','6906123456','+79061234567','volkov@example.ru'),
(8,'Морозова','Ольга','Павловна','6908 890123','6907123456','+79071234567','morozova@example.ru');
INSERT IGNORE INTO rentals (id,car_id,client_id,start_date,end_date_planned,return_date,daily_rate,total_cost,status) VALUES
(1,1,1,'2026-01-10','2026-01-13','2026-01-13',1800,5400,'closed'),
(2,2,2,'2026-01-18','2026-01-20',NULL,1800,3600,'cancelled'),
(3,3,3,'2026-02-02','2026-02-05','2026-02-07',1800,9000,'closed'),
(4,4,4,'2026-02-14','2026-02-18','2026-02-18',3200,12800,'closed'),
(5,5,5,'2026-03-01','2026-03-04',NULL,3200,9600,'cancelled'),
(6,6,6,'2026-03-10','2026-03-12','2026-03-12',3200,6400,'closed'),
(7,7,7,'2026-04-03','2026-04-06','2026-04-08',5600,19600,'closed'),
(8,8,8,'2026-04-20','2026-04-22','2026-04-22',5600,11200,'closed'),
(9,9,1,'2026-05-05','2026-05-09',NULL,4900,19600,'cancelled'),
(10,10,2,'2026-05-15','2026-05-18','2026-05-18',4900,14700,'closed'),
(11,1,3,'2026-06-01','2026-06-03','2026-06-03',1800,3600,'closed'),
(12,2,4,'2026-06-10','2026-06-14',NULL,1800,7200,'active');
UPDATE cars SET status='rented' WHERE id=2;
