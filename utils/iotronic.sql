-- MySQL Script generated by MySQL Workbench
-- lun 04 apr 2016 15:41:37 CEST
-- Model: New Model    Version: 1.0
-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';

-- -----------------------------------------------------
-- Schema iotronic
-- -----------------------------------------------------
DROP SCHEMA IF EXISTS `iotronic` ;

-- -----------------------------------------------------
-- Schema iotronic
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `iotronic` DEFAULT CHARACTER SET utf8 ;
USE `iotronic` ;

-- -----------------------------------------------------
-- Table `iotronic`.`conductors`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `iotronic`.`conductors` ;

CREATE TABLE IF NOT EXISTS `iotronic`.`conductors` (
  `created_at` DATETIME NULL DEFAULT NULL,
  `updated_at` DATETIME NULL DEFAULT NULL,
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `hostname` VARCHAR(255) NOT NULL,
  `online` TINYINT(1) NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `uniq_conductors0hostname` (`hostname` ASC))
ENGINE = InnoDB
AUTO_INCREMENT = 6
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `iotronic`.`wampagents`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `iotronic`.`wampagents` ;

CREATE TABLE IF NOT EXISTS `iotronic`.`wampagents` (
  `created_at` DATETIME NULL DEFAULT NULL,
  `updated_at` DATETIME NULL DEFAULT NULL,
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `hostname` VARCHAR(255) NOT NULL,
  `wsurl` VARCHAR(255) NOT NULL,
  `online` TINYINT(1) NULL DEFAULT NULL,
  `ragent` TINYINT(1) NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `uniq_wampagents0hostname` (`hostname` ASC))
ENGINE = InnoDB
AUTO_INCREMENT = 6
DEFAULT CHARACTER SET = utf8;


-- -----------------------------------------------------
-- Table `iotronic`.`boards`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `iotronic`.`boards` ;

CREATE TABLE IF NOT EXISTS `iotronic`.`boards` (
  `created_at` DATETIME NULL DEFAULT NULL,
  `updated_at` DATETIME NULL DEFAULT NULL,
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `uuid` VARCHAR(36) NOT NULL,
  `code` VARCHAR(25) NOT NULL,
  `status` VARCHAR(15) NULL DEFAULT NULL,
  `name` VARCHAR(255) NULL DEFAULT NULL,
  `type` VARCHAR(255) NOT NULL,
  `agent` VARCHAR(255) NULL DEFAULT NULL,
  `owner` VARCHAR(36) NOT NULL,
  `project` VARCHAR(36) NOT NULL,
  `mobile` TINYINT(1) NOT NULL DEFAULT '0',
  `config` TEXT NULL DEFAULT NULL,
  `extra` TEXT NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `uuid` (`uuid` ASC),
  UNIQUE INDEX `code` (`code` ASC))
ENGINE = InnoDB
AUTO_INCREMENT = 132
DEFAULT CHARACTER SET = utf8;


-- -----------------------------------------------------
-- Table `iotronic`.`locations`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `iotronic`.`locations` ;

CREATE TABLE IF NOT EXISTS `iotronic`.`locations` (
  `created_at` DATETIME NULL DEFAULT NULL,
  `updated_at` DATETIME NULL DEFAULT NULL,
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `longitude` VARCHAR(18) NULL DEFAULT NULL,
  `latitude` VARCHAR(18) NULL DEFAULT NULL,
  `altitude` VARCHAR(18) NULL DEFAULT NULL,
  `board_id` INT(11) NOT NULL,
  PRIMARY KEY (`id`),
  INDEX `board_id` (`board_id` ASC),
  CONSTRAINT `location_ibfk_1`
    FOREIGN KEY (`board_id`)
    REFERENCES `iotronic`.`boards` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB
AUTO_INCREMENT = 6
DEFAULT CHARACTER SET = utf8;


-- -----------------------------------------------------
-- Table `iotronic`.`sessions`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `iotronic`.`sessions` ;

CREATE TABLE IF NOT EXISTS `iotronic`.`sessions` (
  `created_at` DATETIME NULL DEFAULT NULL,
  `updated_at` DATETIME NULL DEFAULT NULL,
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `valid` TINYINT(1) NOT NULL DEFAULT '1',
  `session_id` VARCHAR(18) NOT NULL,
  `board_uuid` VARCHAR(36) NOT NULL,
  `board_id` INT(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `session_id` (`session_id` ASC),
  INDEX `session_board_id` (`board_id` ASC),
  CONSTRAINT `session_board_id`
    FOREIGN KEY (`board_id`)
    REFERENCES `iotronic`.`boards` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB
AUTO_INCREMENT = 10
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `iotronic`.`services`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `iotronic`.`services` ;

CREATE TABLE IF NOT EXISTS `iotronic`.`services` (
  `created_at` DATETIME NULL DEFAULT NULL,
  `updated_at` DATETIME NULL DEFAULT NULL,
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `uuid` VARCHAR(36) NOT NULL,
  `name` VARCHAR(255) NULL DEFAULT NULL,
  `port` INT(5) NOT NULL,
  `project` VARCHAR(36) NOT NULL,
  `protocol` VARCHAR(3) NOT NULL,
  `extra` TEXT NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `uuid` (`uuid` ASC))
ENGINE = InnoDB
AUTO_INCREMENT = 132
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `iotronic`.`exposed_services`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `iotronic`.`exposed_services` ;


CREATE TABLE IF NOT EXISTS `iotronic`.`exposed_services` (
  `created_at` DATETIME NULL DEFAULT NULL,
  `updated_at` DATETIME NULL DEFAULT NULL,
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `board_uuid` VARCHAR(36) NOT NULL,
  `service_uuid` VARCHAR(36) NOT NULL,
  `public_port` INT(5) NOT NULL,
  PRIMARY KEY (`id`),
  INDEX `board_uuid` (`board_uuid` ASC),
  CONSTRAINT unique_index
  UNIQUE (service_uuid, board_uuid),
  CONSTRAINT `fk_board_uuid`
    FOREIGN KEY (`board_uuid`)
    REFERENCES `iotronic`.`boards` (`uuid`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  INDEX `service_uuid` (`service_uuid` ASC),
  CONSTRAINT `service_uuid`
    FOREIGN KEY (`service_uuid`)
    REFERENCES `iotronic`.`services` (`uuid`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB
AUTO_INCREMENT = 132
DEFAULT CHARACTER SET = utf8;

SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;


-- insert testing boards
INSERT INTO `boards` VALUES
  ('2017-02-20 10:38:26',NULL,'','f3961f7a-c937-4359-8848-fb64aa8eeaaa','12345','registered','laptop-14','server',NULL,'eee383360cc14c44b9bf21e1e003a4f3','4adfe95d49ad41398e00ecda80257d21',0,'{}','{}'),
  ('2017-02-20 10:38:45',NULL,'','e9bee8d9-7270-5323-d3e9-9875ba9c5753','yunyun','registered','yun-22','yun',NULL,'13ae14174aa1424688a75253ef814261','3c1e2e2c4bac40da9b4b1d694da6e2a1',0,'{}','{}'),
  ('2017-02-20 10:38:45',NULL,'','96b69f1f-0188-48cc-abdc-d10674144c68','567','registered','yun-30','yun',NULL,'13ae14174aa1424688a75253ef814261','3c1e2e2c4bac40da9b4b1d694da6e2a1',0,'{}','{}'),
  ('2017-02-20 10:39:08',NULL,'','65f9db36-9786-4803-b66f-51dcdb60066e','test','registered','test','server',NULL,'eee383360cc14c44b9bf21e1e003a4f3','4adfe95d49ad41398e00ecda80257d21',0,'{}','{}');
INSERT INTO `locations` VALUES
  ('2017-02-20 10:38:26',NULL,'','2','1','3',132),
  ('2017-02-20 10:38:45',NULL,'','15.5966863','38.2597708','70',133),
  ('2017-02-20 10:38:45',NULL,'','15.5948288','38.259486','18',134),
  ('2017-02-20 10:39:08',NULL,'','2','1','3',135);
# INSERT INTO `plugins` VALUES
#     ('2017-02-20 10:38:26',NULL,132,'edff22cd-9148-4ad8-b35b-51dcdb60066e','runner','0','V# Copyright 2017 MDSLAB - University of Messina\u000a# All Rights Reserved.\u000a#\u000a# Licensed under the Apache License, Version 2.0 (the "License"); you may\u000a# not use this file except in compliance with the License. You may obtain\u000a# a copy of the License at\u000a#\u000a# http://www.apache.org/licenses/LICENSE-2.0\u000a#\u000a# Unless required by applicable law or agreed to in writing, software\u000a# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT\u000a# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the\u000a# License for the specific language governing permissions and limitations\u000a# under the License.\u000a\u000afrom iotronic_lightningrod.plugins import Plugin\u000a\u000afrom oslo_log import log as logging\u000aLOG = logging.getLogger(__name__)\u000a\u000a# User imports\u000aimport time\u000a\u000a\u000a\u000aclass Worker(Plugin.Plugin):\u000a    def __init__(self, name, th_result, plugin_conf=None):\u000a        super(Worker, self).__init__(name, th_result, plugin_conf)\u000a\u000a    def run(self):\u000a        LOG.info("Plugin " + self.name + " starting...")\u000a        while(self._is_running):\u000a            print(self.plugin_conf[''message''])\u000a            time.sleep(1) \u000a
# p1
# .',0,'{}','eee383360cc14c44b9bf21e1e003a4f3')
#   ('2017-02-20 10:38:26',NULL,133,'edff22cd-9148-4ad8-b35b-c0c80abf1e8a','zero','0','Vfrom iotronic_lightningrod.plugins import Plugin\u000a\u000afrom oslo_log import log as logging\u000a\u000aLOG = logging.getLogger(__name__)\u000a\u000a\u000a# User imports\u000a\u000a\u000aclass Worker(Plugin.Plugin):\u000a   def __init__(self, name, is_running):\u000a       super(Worker, self).__init__(name, is_running)\u000a\u000a   def run(self):\u000a       LOG.info("Plugin process completed!")\u000a       #self.Done()
# p1
# .',1,'{}','eee383360cc14c44b9bf21e1e003a4f3');

