import time
import functools
import json
import inspect
from typing import Callable, Any, Optional, Dict, Union
from fastapi import Request, HTTPException
from datetime import datetime
from pydantic import BaseModel
from sqlmodel import Session, select
import traceback
from sqlbot_xpack.audit.curd.audit import build_resource_union_query
from common.audit.models.log_model import OperationType, OperationStatus, SystemLog
from common.audit.schemas.request_context import RequestContext
from apps.system.crud.user import get_user_by_account
from apps.system.schemas.system_schema import UserInfoDTO, BaseUserDTO
from sqlalchemy import and_, select

from common.core.db import engine



def get_resource_name_by_id_and_module(session, resource_id: Any, module: str) -> Optional[str]:
    resource_union_query = build_resource_union_query()
    resource_alias = resource_union_query.alias("resource")

    if isinstance(resource_id, list):
        # 处理列表情况
        if not resource_id:
            return None

        # 构建查询，使用 IN 条件
        query = select(
            resource_alias.c.name
        ).where(
            and_(
                resource_alias.c.id.in_([str(id_) for id_ in resource_id]),
                resource_alias.c.module == module
            )
        )
        # 执行查询并获取所有结果
        results = session.execute(query).scalars().all()

        # 用逗号连接所有名称
        return ",".join(results) if results else None
    else:
        # 处理单个字符串情况
        query = select(
            resource_alias.c.name
        ).where(
            and_(
                resource_alias.c.id == str(resource_id),
                resource_alias.c.module == module
            )
        )
        return session.execute(query).scalar()


class LogConfig(BaseModel):
    operation_type: OperationType
    operation_detail: str = None
    module: Optional[str] = None

    # Extract the expression of resource ID from the parameters
    resource_id_expr: Optional[str] = None

    # Extract the expression for resource ID from the returned result
    result_id_expr: Optional[str] = None

    # Extract the expression for resource name or other info from the returned result
    remark_expr: Optional[str] = None

    # Is it only recorded upon success
    save_on_success_only: bool = False

    # Whether to ignore errors (i.e. record them as successful even when they occur)
    ignore_errors: bool = False

    # Whether to extract request parameters
    extract_params: bool = True

    # Delay recording (if the resource ID needs to be extracted from the result, it can be set to True)
    delay_logging: bool = False


class SystemLogger:
    @staticmethod
    async def create_log(
            session: Session,
            operation_type: OperationType,
            operation_detail: str,
            user: Optional[UserInfoDTO] = None,
            status: OperationStatus = OperationStatus.SUCCESS,
            ip_address: Optional[str] = None,
            user_agent: Optional[str] = None,
            execution_time: int = 0,
            error_message: Optional[str] = None,
            module: Optional[str] = None,
            resource_id: Any = None,
            request_method: Optional[str] = None,
            request_path: Optional[str] = None,
            remark: Optional[str] = None
    ):
        try:
            log = SystemLog(
                operation_type=operation_type,
                operation_detail=operation_detail,
                user_id=user.id if user else None,
                user_name=user.username if user else None,
                operation_status=status,
                ip_address=ip_address,
                user_agent=user_agent,
                execution_time=execution_time,
                error_message=error_message,
                module=module,
                resource_id=resource_id,
                request_method=request_method,
                request_path=request_path,
                created_at=datetime.now(),
                remark=remark
            )
            session.add(log)
            session.commit()
            return log
        except Exception as e:
            session.rollback()
            print(f"[SystemLogger] Log -14 : {str(traceback.format_exc())}")
            print(f"Failed to create system log: {e}")
            return None

    @staticmethod
    def get_client_info(request: Request) -> Dict[str, Optional[str]]:
        """Obtain client information"""
        ip_address = None
        user_agent = None

        if request:
            # Obtain IP address
            if request.client:
                ip_address = request.client.host
            # Attempt to obtain the real IP from X-Forwarded-For
            if "x-forwarded-for" in request.headers:
                ip_address = request.headers["x-forwarded-for"].split(",")[0].strip()

            # Get User Agent
            user_agent = request.headers.get("user-agent")

        return {
            "ip_address": ip_address,
            "user_agent": user_agent
        }

    @staticmethod
    def extract_value_from_object(expression: str, obj: Any):
        """
        Extract values from objects based on expressions
        support:
        -Object attribute: 'user. id'
        -Dictionary key: 'data ['id'] '
        -List index: 'items [0]. id'
        """
        if not expression or obj is None:
            return None

        if expression == 'result_self':
            return obj

        try:
            # Handling point separated attribute access
            parts = expression.split('.')
            current = obj

            for part in parts:
                if not current:
                    return None

                # Handle dictionary key access, such as data ['id ']
                if '[' in part and ']' in part:
                    import re
                    # Extract key names, such as data ['id '] ->key='id'
                    match = re.search(r"\[['\"]?([^\]'\"\]]+)['\"]?\]", part)
                    if match:
                        key = match.group(1)
                        # Get Object Part
                        obj_part = part.split('[')[0]
                        if hasattr(current, obj_part):
                            current = getattr(current, obj_part)
                        elif isinstance(current, dict) and obj_part in current:
                            current = current[obj_part]
                        else:
                            return None

                        # Get key value
                        if isinstance(current, dict) and key in current:
                            current = current[key]
                        elif hasattr(current, key):
                            current = getattr(current, key)
                        elif isinstance(current, list) and key.isdigit():
                            index = int(key)
                            if 0 <= index < len(current):
                                current = current[index]
                            else:
                                return None
                        else:
                            return None
                    else:
                        return None

                # Process list indexes, such as items.0.id
                elif part.isdigit() and isinstance(current, (list, tuple)):
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None

                # Normal attribute access
                else:
                    if hasattr(current, part):
                        current = getattr(current, part)
                    elif isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return None

            return current if current is not None else None

        except Exception:
            return None

    @staticmethod
    def extract_resource_id(
            expression: Optional[str],
            source: Any,
            source_type: str = "args"  # args, kwargs, result
    ):
        """Extract resource IDs from different sources"""
        if not expression:
            return None

        try:
            if source_type == "result":
                # Extract directly from the result object
                return SystemLogger.extract_value_from_object(expression, source)

            elif source_type == "args":
                # Extract from function parameters
                if isinstance(source, tuple) and len(source) > 0:
                    # The first element is the function itself
                    func_args = source[0] if isinstance(source[0], tuple) else source

                    # Processing args [index] expression
                    if expression.startswith("args["):
                        import re
                        pattern = r"args\[(\d+)\]"
                        match = re.match(pattern, expression)
                        if match:
                            index = int(match.group(1))
                            if index < len(func_args):
                                value = func_args[index]
                                return value if value is not None else None

                    # Process attribute expressions
                    return SystemLogger.extract_value_from_object(expression, func_args)

            elif source_type == "kwargs":
                # Extract from keyword parameters
                if isinstance(source, dict):
                    # Simple parameter name
                    if expression in source:
                        value = source[expression]
                        return value if value is not None else None

                    # complex expression
                    return SystemLogger.extract_value_from_object(expression, source)

            return None

        except Exception:
            return None

    @staticmethod
    def extract_from_function_params(
            expression: Optional[str],
            func_args: tuple,
            func_kwargs: dict
    ):
        """Extract values from function parameters"""
        if not expression:
            return None

        # Attempt to extract from location parameters
        result = SystemLogger.extract_resource_id(expression, func_args, "args")
        if result:
            return result

        # Attempt to extract from keyword parameters
        result = SystemLogger.extract_resource_id(expression, func_kwargs, "kwargs")
        if result:
            return result

        # Attempt to encapsulate parameters as objects for extraction
        try:
            if func_args:
                # Create a dictionary containing all parameters
                params_dict = {}

                # Add location parameters
                for i, arg in enumerate(func_args):
                    params_dict[f"arg_{i}"] = arg

                # Add keyword parameters
                params_dict.update(func_kwargs)

                # Attempt to extract from the dictionary
                return SystemLogger.extract_resource_id(expression, params_dict, "kwargs")
        except:
            pass

        return None

    @staticmethod
    def get_current_user(request: Optional[Request]):
        """Retrieve current user information from the request"""
        if not request:
            return None
        try:
            current_user = getattr(request.state, 'current_user', None)
            if current_user:
                return current_user
        except:
            pass

        return None

    @staticmethod
    def extract_request_params(request: Optional[Request]):
        """Extract request parameters"""
        if not request:
            return None

        try:
            params = {}

            # query parameters
            if request.query_params:
                params["query"] = dict(request.query_params)

            # path parameter
            if request.path_params:
                params["path"] = dict(request.path_params)

            # Head information (sensitive information not recorded)
            headers = {}
            for key, value in request.headers.items():
                if key.lower() not in ["authorization", "cookie", "set-cookie"]:
                    headers[key] = value
            if headers:
                params["headers"] = headers

            # Request Body - Only records Content Type and Size
            content_type = request.headers.get("content-type", "")
            content_length = request.headers.get("content-length")
            params["body_info"] = {
                "content_type": content_type,
                "content_length": content_length
            }

            return json.dumps(params, ensure_ascii=False, default=str)

        except Exception:
            return None

    @classmethod
    async def create_log_record(
            cls,
            config: LogConfig,
            status: OperationStatus,
            execution_time: int,
            error_message: Optional[str] = None,
            resource_id: Any = None,
            resource_name: Optional[str] = None,
            request: Optional[Request] = None,
            remark: Optional[str] = None,
            oid: int = -1,
            opt_type_ref : OperationType = None,
    ) -> Optional[SystemLog]:
        """Create log records"""
        try:
            print(f"[SystemLogger] Log -9")
            # Obtain user information
            user_info = cls.get_current_user(request)
            user_id = user_info.id if user_info else -1
            user_name = user_info.name if user_info else '-1'
            if config.operation_type == OperationType.LOGIN:
                user_id = resource_id
                user_name = resource_name

            # Obtain client information
            client_info = cls.get_client_info(request)
            # Get request parameters
            request_params = None
            if config.extract_params:
                request_params = cls.extract_request_params(request)

            print(f"[SystemLogger-Info] :user_info {str(user_info)},oid {str(oid)}")
            # Create log object
            log = SystemLog(
                operation_type=opt_type_ref if opt_type_ref else config.operation_type,
                operation_detail=config.operation_detail,
                user_id=user_id,
                user_name=user_name,
                oid=user_info.oid if user_info else oid,
                operation_status=status,
                ip_address=client_info.get("ip_address"),
                user_agent=client_info.get("user_agent"),
                execution_time=execution_time,
                error_message=error_message,
                module=config.module,
                resource_id=str(resource_id),
                resource_name=str(resource_name),
                request_method=request.method if request else None,
                request_path=request.url.path if request else None,
                request_params=request_params,
                create_time=datetime.now(),
                remark=remark
            )

            with Session(engine) as session:
                print(f"[SystemLogger] Log -10")
                session.add(log)
                session.commit()
                session.refresh(log)
                return log

        except Exception as e:
            print(f"[SystemLogger] Failed to create log: {str(traceback.format_exc())}")
            return None


def system_log(config: Union[LogConfig, Dict]):
    """
    System log annotation decorator, supports extracting resource IDs from returned results

    Usage example:
    @system_log({
    "operation_type": OperationType.CREATE,
    Operation_detail ":" Create User ",
    "module": "user",
    'result_id_expr ':' id '# Extract the id field from the returned result
    })
    """
    # If a dictionary is passed in, convert it to a LogConfig object
    if isinstance(config, dict):
        config = LogConfig(**config)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status = OperationStatus.SUCCESS
            error_message = None
            request = None
            resource_id = None
            resource_name = None
            remark = None
            oid = -1
            opt_type_ref = None

            try:
                # Get current request
                request = RequestContext.get_request()
                print(f"[SystemLogger] Log -1 : {str(request)}")

                # Step 1: Attempt to extract the resource ID from the parameters
                if config.resource_id_expr:
                    resource_id = SystemLogger.extract_from_function_params(
                        config.resource_id_expr,
                        args,
                        kwargs
                    )
                print(f"[SystemLogger] Log -2 : {str(resource_id)}")
                if config.remark_expr:
                    remark = SystemLogger.extract_from_function_params(
                        config.remark_expr,
                        args,
                        kwargs
                    )

                if config.operation_type == OperationType.LOGIN:
                    input_account_dec = SystemLogger.extract_from_function_params(
                        "form_data.username",
                        args,
                        kwargs
                    )
                    from common.utils.crypto import sqlbot_decrypt
                    input_account = await sqlbot_decrypt(input_account_dec)
                    with Session(engine) as session:
                        userInfo = get_user_by_account(session=session, account=input_account)
                        if userInfo is not None:
                            resource_id = userInfo.id
                            resource_name = userInfo.name
                            oid = userInfo.oid
                        else:
                            resource_id = -1
                            oid = -1
                            resource_name = '-' + input_account
                print(f"[SystemLogger] Log -3 : {str(resource_id)}")
                if config.operation_type == OperationType.DELETE:
                    with Session(engine) as session:
                        resource_name = get_resource_name_by_id_and_module(session, resource_id, config.module)

                if config.operation_type == OperationType.CREATE_OR_UPDATE:
                    opt_type_ref = OperationType.UPDATE if resource_id is not None else OperationType.CREATE
                else:
                    opt_type_ref = config.operation_type
                print(f"[SystemLogger] Log -4 : {str(opt_type_ref)}")
                # Execute the original function
                result = await func(*args, **kwargs)
                print(f"[SystemLogger] Log -5 : {str(result)}")
                # Step 2: If the resource ID is configured to be extracted from the results and has not been extracted before
                if config.result_id_expr and not resource_id and result:
                    resource_id = SystemLogger.extract_resource_id(
                        config.result_id_expr,
                        result,
                        "result"
                    )
                if config.operation_type != OperationType.DELETE:
                    with Session(engine) as session:
                        resource_name = get_resource_name_by_id_and_module(session, resource_id, config.module)
                print(f"[SystemLogger] Log -6 : {str(resource_name)}")
                return result

            except Exception as e:
                print(f"[SystemLogger] Log -6 : {str(traceback.format_exc())}")
                status = OperationStatus.FAILED
                error_message = str(e)

                # If it is an HTTPException, retrieve the status code
                if isinstance(e, HTTPException):
                    error_message = f"HTTP {e.status_code}: {e.detail}"

                # If configured to ignore errors, mark as successful
                if config.ignore_errors:
                    status = OperationStatus.SUCCESS

                raise e

            finally:
                # If configured to only record on success and the current status is failure, skip
                if config.save_on_success_only and status == OperationStatus.FAILED:
                    return

                # Calculate execution time
                execution_time = int((time.time() - start_time) * 1000)
                print(f"[SystemLogger] Log -8 ")
                # Asynchronous creation of log records
                try:
                    await SystemLogger.create_log_record(
                        config=config,
                        status=status,
                        execution_time=execution_time,
                        error_message=error_message,
                        resource_id=resource_id,
                        resource_name=resource_name,
                        remark=remark,
                        request=request,
                        oid=oid,
                        opt_type_ref=opt_type_ref
                    )
                except Exception as log_error:
                    print(f"[SystemLogger] Log -12 : {str(traceback.format_exc())}")
                    print(f"[SystemLogger] Log creation failed: {log_error}")

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            status = OperationStatus.SUCCESS
            error_message = None
            request = None
            resource_id = None
            resource_name = None
            result = None

            try:
                # Get current request
                request = RequestContext.get_request()

                # Extract resource ID from parameters
                if config.resource_id_expr:
                    resource_id = SystemLogger.extract_from_function_params(
                        config.resource_id_expr,
                        args,
                        kwargs
                    )

                # Obtain client information
                if config.operation_type == OperationType.DELETE:
                    with Session(engine) as session:
                        resource_name = get_resource_name_by_id_and_module(session, resource_id, config.module)

                # Execute the original function
                result = func(*args, **kwargs)

                # Extract resource ID from the results
                if config.result_id_expr and not resource_id and result:
                    resource_id = SystemLogger.extract_resource_id(
                        config.result_id_expr,
                        result,
                        "result"
                    )

                if config.operation_type != OperationType.DELETE:
                    with Session(engine) as session:
                        resource_name = get_resource_name_by_id_and_module(session, resource_id, config.module)

                return result

            except Exception as e:
                status = OperationStatus.FAILED
                error_message = str(e)

                if isinstance(e, HTTPException):
                    error_message = f"HTTP {e.status_code}: {e.detail}"

                if config.ignore_errors:
                    status = OperationStatus.SUCCESS

                raise e

            finally:
                if config.save_on_success_only and status == OperationStatus.FAILED:
                    return

                execution_time = int((time.time() - start_time) * 1000)

                # In the synchronous version, we still create logs asynchronously
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(
                            SystemLogger.create_log_record(
                                config=config,
                                status=status,
                                execution_time=execution_time,
                                error_message=error_message,
                                resource_id=resource_id,
                                resource_name=resource_name,
                                request=request
                            )
                        )
                    else:
                        asyncio.run(
                            SystemLogger.create_log_record(
                                config=config,
                                status=status,
                                execution_time=execution_time,
                                error_message=error_message,
                                resource_id=resource_id,
                                request=request
                            )
                        )
                except Exception as log_error:
                    print(f"[SystemLogger] Log -13 : {str(traceback.format_exc())}")
                    print(f"[SystemLogger] Log creation failed: {log_error}")

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
