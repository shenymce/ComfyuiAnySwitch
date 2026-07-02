/**
 * ComfyuiAnySwitch — 前端动态 widget + slot 管理
 *
 * case_N widget 和 input_N slot 完全由 JS 动态创建/删除，
 * 数量始终严格等于 item_count。
 * input_default slot 由后端静态声明，始终保留在最后。
 *
 * GitHub: https://github.com/shenymce/ComfyuiAnySwitch
 * 参考：KJNodes SetNode/GetNode（LiteGraph addWidget callback 机制）
 */

import { app } from "../../scripts/app.js";

const NODE_TYPE = "AnyInputSwitch";
const MAX_ITEMS = 64;

app.registerExtension({
    name: "AnyInputSwitch.DynamicIO",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_TYPE) return;

        // ── 节点创建后立即同步 ──────────────────────────────────
        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origCreated?.apply(this, arguments);

            // 替换 item_count widget 的 callback，使其触发 _syncIO
            const countWidget = this.widgets?.find(w => w.name === "item_count");
            if (countWidget) {
                const origCallback = countWidget.callback;
                countWidget.callback = (value, ...args) => {
                    // 先调原始 callback（如果有）
                    if (origCallback) origCallback.call(countWidget, value, ...args);
                    const n = Math.max(1, Math.min(MAX_ITEMS, parseInt(value) || 1));
                    this._syncIO(n);
                };
            }

            // 用当前值初始化
            this._syncIO(this._getCount());
        };

        // ── 工作流加载时恢复 ────────────────────────────────────
        const origConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            origConfigure?.apply(this, arguments);
            this._syncIO(this._getCount());
        };

        // ── 读取 item_count 当前值 ──────────────────────────────
        nodeType.prototype._getCount = function () {
            const w = this.widgets?.find(w => w.name === "item_count");
            return Math.max(1, Math.min(MAX_ITEMS, parseInt(w?.value) || 1));
        };

        // ── 核心同步：case widgets + input slots 对齐到 count ──
        nodeType.prototype._syncIO = function (count) {
            if (count == null) count = this._getCount();

            // ===== 1. 同步 case_N widgets =====
            const existingCaseNames = (this.widgets || [])
                .filter(w => /^case_\d+$/.test(w.name))
                .map(w => w.name);

            const existingCount = existingCaseNames.length;

            if (existingCount > count) {
                // 删多余：从大到小
                for (let i = existingCount; i > count; i--) {
                    const w = this.widgets.find(w => w.name === `case_${i}`);
                    if (w) {
                        const idx = this.widgets.indexOf(w);
                        this.widgets.splice(idx, 1);
                        // 移除 DOM 元素
                        if (w.element?.parentNode) {
                            w.element.parentNode.removeChild(w.element);
                        }
                    }
                }
            } else if (existingCount < count) {
                // 补缺少：逐个创建
                for (let i = existingCount + 1; i <= count; i++) {
                    this._addCaseWidget(i);
                }
            }

            // ===== 2. 同步 input_N slots =====
            for (let i = MAX_ITEMS; i > count; i--) {
                const idx = (this.inputs || []).findIndex(s => s.name === `input_${i}`);
                if (idx >= 0) this.removeInput(idx);
            }
            for (let i = 1; i <= count; i++) {
                if (!(this.inputs || []).find(s => s.name === `input_${i}`)) {
                    this.addInput(`input_${i}`, "*");
                }
            }

            // ===== 3. 保证 input_default 最后 =====
            this._ensureDefaultLast();

            this.setSize(this.computeSize());
            this.setDirtyCanvas(true, true);
        };

        // ── 添加单个 case_N widget ─────────────────────────────
        nodeType.prototype._addCaseWidget = function (i) {
            const widget = this.addWidget(
                "text",          // LiteGraph widget type
                `case_${i}`,     // name
                "",              // default value
                () => {},        // callback（值变化不需要额外行为）
                {}               // options
            );
            return widget;
        };

        // ── 确保 input_default 在最后 ──────────────────────────
        nodeType.prototype._ensureDefaultLast = function () {
            if (!this.inputs) return;
            const defIdx = this.inputs.findIndex(s => s.name === "input_default");
            if (defIdx < 0) {
                this.addInput("input_default", "*");
                return;
            }
            const last = this.inputs.length - 1;
            if (defIdx !== last) {
                const [moved] = this.inputs.splice(defIdx, 1);
                this.inputs.push(moved);
            }
        };
    },
});
