from flask import Blueprint, request, jsonify
# 暂时注释JWT相关导入
# from flask_jwt_extended import jwt_required
import re
from app.services.binance_client import get_client_by_email
import logging

logger = logging.getLogger(__name__)

# 修改为空字符串URL前缀，因为已经有了父蓝图的前缀/api/subaccounts
positions_bp = Blueprint('positions', __name__, url_prefix='/futures-positions')

logger.info("创建positions_bp蓝图，URL前缀: /futures-positions")

# 添加验证函数
def validate_email(email):
    """
    验证邮箱格式是否正确
    """
    if not email:
        return False
        
    # 使用正则表达式验证邮箱格式
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

@positions_bp.route('', methods=['POST'])
# 暂时注释掉JWT验证
# @jwt_required()
def get_futures_positions():
    """
    获取子账号的期货持仓信息
    
    请求体:
    {
        "emails": ["子账号邮箱1", "子账号邮箱2", ...],
        "user_id": "用户ID" // 可选
    }
    """
    try:
        logger.info("收到get_futures_positions请求")
        data = request.get_json()
        
        # 验证参数
        if not data or 'emails' not in data:
            return jsonify({
                "success": False,
                "error": "缺少子账号邮箱参数"
            }), 400
        
        emails = data.get('emails', [])
        
        # 确保emails是列表
        if not isinstance(emails, list):
            emails = [emails]
        
        # 验证邮箱
        for email in emails:
            if not validate_email(email):
                return jsonify({
                    "success": False,
                    "error": f"邮箱格式不正确: {email}"
                }), 400
        
        # 获取所有账号的持仓信息
        positions_data = []
        
        for email in emails:
            # 获取子账号API客户端
            client = get_client_by_email(email)
            if not client:
                logger.error(f"获取子账号 {email} 的API客户端失败")
                continue
                
            try:
                # 直接使用客户端调用API
                result = client._send_request(
                    method='GET',
                    url='/papi/v1/account',
                    signed=True
                )
                
                if result:
                    positions = result.get('positions', [])
                    # 过滤出有持仓的数据
                    active_positions = [position for position in positions if float(position.get('positionAmt', 0)) != 0]
                    
                    if active_positions:
                        positions_data.extend(active_positions)
                else:
                    # 记录错误但继续处理其他账号
                    logger.error(f"获取账号 {email} 的持仓信息失败: API返回空结果")
            except Exception as e:
                logger.exception(f"获取账号 {email} 的持仓信息异常: {str(e)}")
        
        return jsonify({
            "success": True,
            "data": positions_data
        })
        
    except Exception as e:
        logger.exception(f"get_futures_positions异常: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"服务器错误: {str(e)}"
        }), 500

@positions_bp.route('/dual-side', methods=['POST'])
# 暂时注释掉JWT验证
# @jwt_required()
def set_position_mode():
    """
    设置U本位合约的持仓模式（单向持仓/双向持仓）
    
    请求体:
    {
        "email": "子账号邮箱",
        "dualSidePosition": true或false  // true为双向持仓，false为单向持仓
    }
    """
    try:
        logger.info(f"[DEBUG] 收到持仓模式设置请求")
        # 尝试从请求中获取JSON数据
        try:
            data = request.get_json(force=True)
            logger.info(f"[DEBUG] 请求数据: {data}")
        except Exception as e:
            logger.error(f"[ERROR] 解析JSON数据失败: {str(e)}")
            logger.error(f"[ERROR] 原始请求内容: {request.data}")
            return jsonify({
                "success": False,
                "error": f"无法解析请求数据: {str(e)}"
            }), 400
        
        # 验证参数
        if not data:
            return jsonify({
                "success": False,
                "error": "请求体为空"
            }), 400
            
        if 'email' not in data:
            return jsonify({
                "success": False,
                "error": "缺少email参数"
            }), 400
            
        if 'dualSidePosition' not in data:
            return jsonify({
                "success": False,
                "error": "缺少dualSidePosition参数"
            }), 400
        
        email = data.get('email')
        dual_side_position = data.get('dualSidePosition')
        logger.info(f"[DEBUG] 请求参数: email={email}, dual_side_position={dual_side_position}")
        
        # 验证邮箱
        if not validate_email(email):
            return jsonify({
                "success": False,
                "error": "邮箱格式不正确"
            }), 400
        
        # 获取子账号API客户端
        client = get_client_by_email(email)
        if not client:
            logger.error(f"[ERROR] 无法获取子账号 {email} 的API客户端")
            return jsonify({
                "success": False,
                "error": f"无法获取子账号 {email} 的API客户端"
            }), 400
            
        # 构造请求体
        params = {
            'dualSidePosition': 'true' if dual_side_position else 'false'
        }
        logger.info(f"[DEBUG] API请求参数: {params}")
        
        # 直接使用客户端调用API
        logger.info(f"[DEBUG] 调用币安API: /papi/v1/um/positionSide/dual")
        result = client._send_request(
            method='POST',
            url='/papi/v1/um/positionSide/dual',
            payload=params,
            signed=True
        )
        logger.info(f"[DEBUG] API调用结果: {result}")
        
        # 处理响应
        if result:
            logger.info(f"[DEBUG] 设置持仓模式成功: {result}")
            return jsonify({
                "success": True,
                "data": result
            })
        else:
            logger.error(f"[ERROR] 设置持仓模式失败: API返回空结果")
            return jsonify({
                "success": False,
                "error": "设置持仓模式失败，API返回空结果"
            }), 400
        
    except Exception as e:
        import traceback
        logger.exception(f"[ERROR] 设置持仓模式异常: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"服务器错误: {str(e)}"
        }), 500 