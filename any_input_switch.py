# ============================================================
# ComfyuiAnySwitch — ComfyUI 自定义节点
# 只执行匹配分支：check_lazy_status + lazy input 机制
# case_N 和 input_N 均在 INPUT_TYPES 中声明（参考 FL_Switch_Big）
# case_N: STRING widget，用于匹配条件
# input_N: lazy input，未匹配分支不参与计算
# input_default: lazy input，无匹配时兜底
# GitHub: https://github.com/shenymce/ComfyuiAnySwitch
# ============================================================

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
    """
    动态多路 Switch 节点。
    item_count 控制 case / input 数量；案例值精确匹配。
    只计算命中分支；无匹配走 input_default。
    """

    @classmethod
    def INPUT_TYPES(cls):
        optional = {
            "input_default": ("*", {"lazy": True}),
        }
        for i in range(1, MAX_ITEMS + 1):
            optional[f"input_{i}"] = ("*", {"lazy": True})
            optional[f"case_{i}"] = ("STRING", {
                "default": "",
                "multiline": False,
            })

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
            "optional": optional,
        }

    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("output",)
    FUNCTION = "switch"
    CATEGORY = "utils"

    DESCRIPTION = (
        "动态多路 Switch 节点。\n"
        "- item_count 控制 case / input 数量\n"
        "- switch_condition 与各 case_N 精确匹配\n"
        "- 命中 case_N → 输出 input_N；无匹配 → 输出 input_default\n"
        "- 未命中分支不参与计算（懒加载）"
    )

    def check_lazy_status(self, item_count, switch_condition, **kwargs):
        """
        返回需要计算的输入名。
        命中分支的 upstream 通过 make_input_strong_link 强制计算，
        其他分支的 upstream 不执行。
        """
        n = int(item_count)
        n = max(1, min(MAX_ITEMS, n))

        for i in range(1, n + 1):
            case_val = kwargs.get(f"case_{i}", "")
            if switch_condition and switch_condition == case_val:
                return [f"input_{i}"]

        # 都不匹配 → 走 default
        return ["input_default"]

    def switch(self, item_count, switch_condition, **kwargs):
        n = int(item_count)
        n = max(1, min(MAX_ITEMS, n))

        for i in range(1, n + 1):
            case_val = kwargs.get(f"case_{i}", "")
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
