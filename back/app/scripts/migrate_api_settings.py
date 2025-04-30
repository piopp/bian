#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
将子账号API设置从JSON文件迁移到数据库
用法: flask run-script migrate_api_settings
"""

import os
import json
import logging
from flask import current_app
from app.models import db
from app.models.account import SubAccountAPISettings

logger = logging.getLogger(__name__)

def migrate_api_settings():
    """
    将子账号API设置从JSON文件迁移到数据库
    """
    try:
        # 获取JSON文件路径
        data_dir = current_app.config.get('DATA_DIR', 'data')
        storage_file = os.path.join(data_dir, 'subaccount_api_settings.json')
        
        # 检查文件是否存在
        if not os.path.exists(storage_file):
            logger.info(f"API设置文件不存在: {storage_file}，无需迁移")
            return True, "JSON文件不存在，无需迁移"
        
        # 读取JSON文件
        try:
            with open(storage_file, 'r', encoding='utf-8') as f:
                api_settings = json.load(f)
        except Exception as e:
            logger.error(f"读取API设置文件失败: {str(e)}")
            return False, f"读取JSON文件失败: {str(e)}"
        
        # 统计计数
        total_count = len(api_settings)
        success_count = 0
        
        # 迁移每个API设置
        for email, settings in api_settings.items():
            api_key = settings.get('apiKey', '')
            api_secret = settings.get('apiSecret', '')
            
            if not api_key or not api_secret:
                logger.warning(f"邮箱 {email} 的API密钥不完整，跳过")
                continue
            
            # 检查是否已存在
            existing = SubAccountAPISettings.query.filter_by(email=email).first()
            
            if existing:
                # 更新现有记录
                existing.api_key = api_key
                existing.api_secret = api_secret
                logger.info(f"更新邮箱 {email} 的API设置")
            else:
                # 创建新记录
                new_setting = SubAccountAPISettings(
                    email=email,
                    api_key=api_key,
                    api_secret=api_secret
                )
                db.session.add(new_setting)
                logger.info(f"创建邮箱 {email} 的API设置")
            
            success_count += 1
        
        # 提交事务
        db.session.commit()
        
        # 备份旧文件
        backup_file = f"{storage_file}.bak"
        os.rename(storage_file, backup_file)
        logger.info(f"JSON文件已备份为: {backup_file}")
        
        return True, f"成功迁移 {success_count}/{total_count} 个API设置到数据库"
    
    except Exception as e:
        db.session.rollback()
        logger.exception(f"迁移API设置失败: {str(e)}")
        return False, f"迁移失败: {str(e)}"

def run():
    """
    脚本入口点
    """
    print("开始迁移子账号API设置...")
    success, message = migrate_api_settings()
    if success:
        print(f"迁移成功: {message}")
        return 0
    else:
        print(f"迁移失败: {message}")
        return 1

if __name__ == "__main__":
    run() 