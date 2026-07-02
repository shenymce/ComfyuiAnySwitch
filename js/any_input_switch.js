/**
 * ComfyuiAnySwitch — IO 同步
 *
 * input_N / case_N 均在后端 INPUT_TYPES 中声明（64 组）。
 * JS 只负责：显示/隐藏 case_N widget，添加/删除多余的 input_N slot。
 * 关键：不删除有连线的 slot（避免连线丢失）。
 *
 * GitHub: https://github.com/shenymce/ComfyuiAnySwitch
 */

import { app } from "../../scripts/app.js";

const NODE_TYPE = "AnyInputSwitch";
const MAX_ITEMS = 64;

app.registerExtension({
    name: "AnyInputSwitch.DynamicIO",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_TYPE) return;

        // ── 新节点/加载时只设 callback，同步延后让连线先恢复 ────
        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origCreated?.apply(this, arguments);

            const countWidget = this.widgets?.find(w => w.name === "item_count");
            if (countWidget) {
                const origCallback = countWidget.callback;
                countWidget.callback = (value, ...args) => {
                    if (origCallback) origCallback.call(countWidget, value, ...args);
                    const n = Math.max(1, Math.min(MAX_ITEMS, parseInt(value) || 1));
                    this._syncIO(n);
                };
            }

            // 初次同步：延迟确保所有 widget 初始完毕
            setTimeout(() => this._syncIO(this._getCount()), 0);
        };

        // ── 加载工作流：在 onConfigure 中延迟同步 ──────────────
        const origConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            origConfigure?.apply(this, arguments);
            setTimeout(() => this._syncIO(this._getCount()), 0);
        };

        nodeType.prototype._getCount = function () {
            const w = this.widgets?.find(w => w.name === "item_count");
            return Math.max(1, Math.min(MAX_ITEMS, parseInt(w?.value) || 1));
        };

        // ── 核心同步 ────────────────────────────────────────────
        nodeType.prototype._syncIO = function (count) {
            if (count == null) count = this._getCount();
            count = Math.max(1, Math.min(MAX_ITEMS, count));

            // ===== case_N widget：显示/隐藏 =====
            for (let i = 1; i <= MAX_ITEMS; i++) {
                const w = this.widgets?.find(w => w.name === `case_${i}`);
                if (w) w.type = i <= count ? "text" : "hidden";
            }

            // ===== input_N slot：添加缺少 & 删除多余（无连线）=====
            for (let n = 1; n <= count; n++) {
                const name = `input_${n}`;
                if (!(this.inputs || []).find(s => s.name === name)) {
                    this.addInput(name, "*");
                }
            }

            // 从后往前检查，只删无连接的
            for (let n = MAX_ITEMS; n > count; n--) {
                const name = `input_${n}`;
                const idx = (this.inputs || []).findIndex(s => s.name === name);
                if (idx >= 0 && this.inputs[idx].link == null) {
                    this.removeInput(idx);
                }
            }

            // ===== input_default 怼到最后 =====
            this._ensureDefaultLast();

            this.setSize(this.computeSize());
            this.setDirtyCanvas(true, true);
        };

        nodeType.prototype._ensureDefaultLast = function () {
            if (!this.inputs) return;
            const defIdx = this.inputs.findIndex(s => s.name === "input_default");
            if (defIdx < 0) return;
            const last = this.inputs.length - 1;
            if (defIdx !== last) {
                const [moved] = this.inputs.splice(defIdx, 1);
                this.inputs.push(moved);
            }
        };
    },
});
