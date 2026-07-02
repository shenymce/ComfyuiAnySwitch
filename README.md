# ComfyuiAnySwitch

ComfyUI 动态多路 Switch 节点 —— 任意数量输入、精确匹配、default 兜底、懒加载。

## 特性

- **无限输入**：通过 `item_count` 参数（1~64）自由控制 case/input 端口数量
- **default 分支**：`input_default` 输入始终存在，无匹配时自动走默认路径
- **懒加载**：仅计算命中的分支，其余分支的上游节点不会被触发
- **任意类型**：`*` 通配端口，支持 IMAGE / LATENT / MODEL / CLIP 等任意 ComfyUI 数据类型

## 安装

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/shenymce/ComfyuiAnySwitch.git
# 无第三方依赖，无需 pip install
```

重启 ComfyUI 即可在 `utils` 分类下找到 **Any Input Switch** 节点。

## 使用

1. 添加节点，调整 `item_count` 设置需要的分支数量
2. 为每个 `case_N` 填写匹配值
3. 给 `switch_condition` 连入条件值（字符串）
4. 给 `input_N` 连入各分支数据
5. `input_default` 接默认路径

匹配逻辑：`switch_condition` 与 `case_N` 做精确字符串比较，命中第一个匹配项即输出对应 `input_N`；全部不匹配时输出 `input_default`。

<img width="897" height="879" alt="image" src="https://github.com/user-attachments/assets/93abb18e-51d1-4df9-931e-88ac8643a8c5" />


## 示例

见 [example.json](./example.json)，可直接拖入 ComfyUI 加载。
