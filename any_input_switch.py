# ============================================================
# ComfyuiAnySwitch — ComfyUI 自定义节点
# item_count 控制 case / input 数量；前端 JS 动态增删 widget & slot
# 懒加载：只计算命中的那条分支；无匹配走 input_default
# GitHub: https://github.com/shenymce/ComfyuiAnySwitch
# ============================================================

class SmartType(str):
    """让 '*' 能与任意类型匹配"""
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
    """
    动态多路 Switch 节点。
    - item_count       : 控制 case / input 端口数量（由前端 JS 同步维护）
    - switch_condition : 条件字符串
    - case_N           : 前端 JS 动态添加的 widget，后端通过 **kwargs 接收
    - input_N          : 前端 JS 动态添加的 slot，任意类型，懒加载
    - input_default    : 无匹配时兜底输入，始终存在
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "item_count": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": MAX_ITEMS,
                    "step": 1,
                    "display": "number",
                }),
                "switch_condition": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
            },
            "optional": {
                # case_N 和 input_N 由前端 JS 动态管理；
                # 后端通过 **kwargs 接收，不在此静态声明
                # input_default 后端静态声明，始终存在
                "input_default": ("*", {"lazy": True}),
            },
        }

    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("output",)
    FUNCTION = "switch"
    CATEGORY = "utils"

    DESCRIPTION = (
        "动态多路 Switch 节点。\n"
        "- item_count 控制 case / input 数量（前端同步，两者始终相等）\n"
        "- switch_condition 与各 case_N 精确匹配\n"
        "- 命中 case_N → 输出 input_N；无匹配 → 输出 input_default\n"
        "- 未命中分支不参与计算（懒加载）"
    )

    def check_lazy_status(self, item_count, switch_condition, **kwargs):
        n = int(item_count)
        matched = False

        for i in range(1, n + 1):
            case_val = kwargs.get(f"case_{i}", "")
            if switch_condition == case_val:
                matched = True
                if kwargs.get(f"input_{i}") is None:
                    return [f"input_{i}"]
                return []  # 已求值，直接返回空

        if not matched:
            if kwargs.get("input_default") is None:
                return ["input_default"]

        return []

    def switch(self, item_count, switch_condition, **kwargs):
        n = int(item_count)

        for i in range(1, n + 1):
            case_val = kwargs.get(f"case_{i}", "")
            if switch_condition == case_val:
                val = kwargs.get(f"input_{i}")
                if val is not None:
                    return (val,)
                break  # 匹配但未连线 → 走 default

        # 无匹配 or input_N 未连线 → default
        return (kwargs.get("input_default"),)


NODE_CLASS_MAPPINGS = {
    "AnyInputSwitch": AnyInputSwitch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnyInputSwitch": "Any Input Switch",
}
