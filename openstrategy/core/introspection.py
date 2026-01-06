import ast
import sys
import typing
from dataclasses import make_dataclass, field
from pathlib import Path
from typing import Any, List, Dict, Optional, Union
from .args import StrategyArgs

def _eval_type(type_node, safe_globals):
    try:
        type_str = ast.unparse(type_node)
        return eval(type_str, safe_globals)
    except Exception:
        return Any

def _is_container_type(type_obj):
    """判断是否为 List 或 Dict 类型"""
    origin = getattr(type_obj, '__origin__', None)
    
    # 处理 List/List[int]
    if type_obj is list or origin is list or origin is List:
        return 'list'
    
    # 处理 Dict/Dict[str, int]
    if type_obj is dict or origin is dict or origin is Dict:
        return 'dict'
        
    return None

def _extract_default_value_node(item):
    """从 AST 中提取赋值语句右边的节点"""
    # Case 1: x: int = 1
    if item.value:
        return item.value
    return None

def load_strategy_args_from_source(file_path: str) -> type:
    path = Path(file_path)
    if not path.exists():
        return StrategyArgs

    try:
        with open(path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except Exception as e:
        print(f"[Warning] AST Parse failed: {e}")
        return StrategyArgs

    target_class_node = None
    
    # 1. 寻找继承自 StrategyArgs 的类
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == 'StrategyArgs':
                    target_class_node = node
                    break
        if target_class_node:
            break
    
    if not target_class_node:
        return StrategyArgs

    # 2. 准备 Eval 环境
    safe_globals = {k: getattr(typing, k) for k in dir(typing)}
    safe_globals.update({'int': int, 'str': str, 'float': float, 'bool': bool, 'dict': dict, 'list': list})

    fields_list = []

    for item in target_class_node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            arg_name = item.target.id
            arg_type = _eval_type(item.annotation, safe_globals)
            
            # 尝试提取默认值
            default_val = None
            has_default = False
            
            value_node = item.value
            
            # 逻辑 A: 简单的赋值 (x = 1)
            if value_node and not (isinstance(value_node, ast.Call) and getattr(value_node.func, 'id', '') == 'field'):
                try:
                    default_val = ast.literal_eval(value_node)
                    has_default = True
                except:
                    pass
            
            # 逻辑 B: 使用了 field() 函数
            elif isinstance(value_node, ast.Call) and getattr(value_node.func, 'id', '') == 'field':
                # 即使使用了 field，我们可能也无法静态解析出值 (如 default_factory)
                # 但我们需要知道"用户定义了默认值"，这样我们必须提供一个 Mock 值给 OmegaConf
                has_default = True 
                
                # 尝试解析 field(default=1) 中的常量
                for keyword in value_node.keywords:
                    if keyword.arg == 'default':
                        try:
                            default_val = ast.literal_eval(keyword.value)
                        except:
                            pass
            
            # === 核心修复逻辑 ===
            container_type = _is_container_type(arg_type)
            
            if has_default:
                if default_val is not None:
                    # 如果成功提取了字面量 (例如 default=1)
                    fields_list.append((arg_name, arg_type, field(default=default_val)))
                else:
                    # 如果有默认值定义 (如 default_factory)，但无法静态提取
                    # 为了骗过 OmegaConf，我们需要根据类型填充一个安全的空值
                    if container_type == 'list':
                        # 对于 List 类型，填充 []
                        fields_list.append((arg_name, arg_type, field(default_factory=list)))
                    elif container_type == 'dict':
                        # 对于 Dict 类型，填充 {}
                        fields_list.append((arg_name, arg_type, field(default_factory=dict)))
                    else:
                        # 对于其他复杂类型，如果无法解析默认值，为了安全，将类型降级为 Optional
                        # 这样 default=None 才是合法的
                        safe_type = Optional[arg_type]
                        fields_list.append((arg_name, safe_type, field(default=None)))
            else:
                # 逻辑 C: 真的没有默认值 (x: int)，那就是必填项
                # 使用 MISSING 让 OmegaConf 知道这是必填的
                from omegaconf import MISSING
                fields_list.append((arg_name, arg_type, field(default=MISSING)))

    # 3. 动态构建
    try:
        DynamicArgs = make_dataclass(
            target_class_node.name,
            fields_list,
            bases=(StrategyArgs,)
        )
        return DynamicArgs
    except Exception as e:
        print(f"[Warning] Failed to construct shadow dataclass: {e}. Fallback to generic.")
        return StrategyArgs