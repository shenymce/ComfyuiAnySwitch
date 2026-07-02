# ============================================================
# ComfyuiAnySwitch — ComfyUI 自定义节点
# 只执行匹配分支：check_lazy_status + lazy input 机制
#
# input_N / input_default: 在 INPUT_TYPES 中声明为 lazy（懒加载需要）
# case_N: 不在 INPUT_TYPES 中（JS 动态管理 widget）
# __case_json: 隐藏字段，存储所有 case 值的 JSON（供 lazy 判断读取）
#
# GitHub: https://github.com/shenymce/ComfyuiAnySwitch
# ============================================================

import json

class SmartType(str):
    def __ne__(self, other):
        if self == "*" or other == "*":
            return False
        selfset = set(self.split(','))
        otherset = set(other.split(','))
        return not selfset.issubset(otherset)


def MakeSmartType(t):
    if isinstance(t, str):
        return SmartType(t)
    return t


def VariantSupport():
    def decorator(cls):
        if hasattr(cls, "INPUT_TYPES"):
            old_input_types = getattr(cls, "INPUT_TYPES")
            def new_input_types(*args, **kwargs):
                types = old_input_types(*args, **kwargs)
                for category in ["required", "optional"]:
                    if category not in types:
                        continue
                    for key, value in types[category].items():
                        if isinstance(value, tuple):
                            types[category][key] = (MakeSmartType(value[0]),) + value[1:]
                return types
            setattr(cls, "INPUT_TYPES", new_input_types)

        if hasattr(cls, "RETURN_TYPES"):
            setattr(cls, "RETURN_TYPES",
                    tuple(MakeSmartType(x) for x in cls.RETURN_TYPES))

        if not hasattr(cls, "VALIDATE_INPUTS"):
            def validate_inputs(input_types):
                inputs = cls.INPUT_TYPES()
                for key, value in input_types.items():
                    if isinstance(value, SmartType):
                        continue
                    expected = None
                    if "required" in inputs and key in inputs["required"]:
                        expected = inputs["required"][key][0]
                    elif "optional" in inputs and key in inputs["optional"]:
                        expected = inputs["optional"][key][0]
                    if expected is not None and MakeSmartType(value) != expected:
                        return f"Invalid type for '{key}': got {value}, expected {expected}"
                return True
            setattr(cls, "VALIDATE_INPUTS", validate_inputs)

        return cls
    return decorator


MAX_ITEMS = 64


@VariantSupport()
class AnyInputSwitch:
    """动态多路 Switch。只计算命中分支；无匹配走 input_default。"""

    @classmethod
    def INPUT_TYPES(cls):
        optional = {
            "input_default": ("*", {"lazy": True}),
            # __case_json 存储所有 case 值的 JSON 字符串（供 check_lazy_status 读取）
            # 前端 JS 负责维护此字段的值
            "__case_json": ("STRING", {
                "default": "{}",
                "multiline": False,
            }),
        }
        for i in range(1, MAX_ITEMS + 1):
            optional[f"input_{i}"] = ("*", {"lazy": True})

        return {
            "required": {
                "item_count": ("INT", {
                    "default": 3, "min": 1, "max": MAX_ITEMS, "step": 1, "display": "number",
                }),
                "switch_condition": ("STRING", {
                    "default": "", "multiline": False,
                }),
            },
            "optional": optional,
        }

    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("output",)
    FUNCTION = "switch"
    CATEGORY = "utils"

    DESCRIPTION = (
        "动态多路 Switch。\n"
        "switch_condition 与各 case_N 精确匹配。\n"
        "命中 → 输出对应 input_N；无匹配 → input_default。\n"
        "未命中分支不参与计算（懒加载）。"
    )

    def check_lazy_status(self, item_count, switch_condition, **kwargs):
        n = int(item_count)
        n = max(1, min(MAX_ITEMS, n))

        # 从 __case_json 解析 case 值
        case_json = kwargs.get("__case_json", "{}")
        try:
            cases = json.loads(case_json)
        except (json.JSONDecodeError, TypeError):
            cases = {}

        for i in range(1, n + 1):
            case_val = cases.get(str(i), "")
            if switch_condition and switch_condition == case_val:
                return [f"input_{i}"]

        return ["input_default"]

    def switch(self, item_count, switch_condition, **kwargs):
        n = int(item_count)
        n = max(1, min(MAX_ITEMS, n))

        # 从 __case_json 解析 case 值
        case_json = kwargs.get("__case_json", "{}")
        try:
            cases = json.loads(case_json)
        except (json.JSONDecodeError, TypeError):
            cases = {}

        for i in range(1, n + 1):
            case_val = cases.get(str(i), "")
            if switch_condition and switch_condition == case_val:
                val = kwargs.get(f"input_{i}")
                if val is not None:
                    return (val,)
                break

        return (kwargs.get("input_default"),)


NODE_CLASS_MAPPINGS = {
    "AnyInputSwitch": AnyInputSwitch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnyInputSwitch": "Any Input Switch",
}
