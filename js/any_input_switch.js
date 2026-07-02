/**
 * ComfyuiAnySwitch — IO 同步
 *
 * 架构：
 * - case_N：不在 INPUT_TYPES 中，JS 用 addWidget/splice 动态管理（无 DOM 操作）
 * - __case_json：在 INPUT_TYPES 中，存储所有 case 值的 JSON（供 check_lazy_status 读取）
 * - input_N：在 INPUT_TYPES 中声明为 lazy，JS 管理 slot 显隐
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

        // ── 同步 __case_json ← case_N widgets ───────────────────
        nodeType.prototype._syncCasesToJson = function () {
            const cases = {};
            for (const w of (this.widgets || [])) {
                if (/^case_\d+$/.test(w.name)) {
                    const num = parseInt(w.name.split("_")[1]);
                    const val = (w.value || "").trim();
                    if (val !== "") {
                        cases[num] = val;
                    }
                }
            }
            const jsonWidget = this.widgets?.find(w => w.name === "__case_json");
            if (jsonWidget) {
                jsonWidget.value = JSON.stringify(cases);
            }
        };

        // ── 同步 case_N widgets ← __case_json ───────────────────
        nodeType.prototype._syncCasesFromJson = function () {
            const jsonWidget = this.widgets?.find(w => w.name === "__case_json");
            if (!jsonWidget) return;
            try {
                const cases = JSON.parse(jsonWidget.value || "{}");
                for (const w of (this.widgets || [])) {
                    if (/^case_\d+$/.test(w.name)) {
                        const num = parseInt(w.name.split("_")[1]);
                        if (cases[num] !== undefined) {
                            w.value = cases[num];
                        }
                    }
                }
            } catch (e) {}
        };

        // ── 创建单个 case_N widget ──────────────────────────────
        nodeType.prototype._addCaseWidget = function (num) {
            const w = this.addWidget("text", `case_${num}`, "", () => {
                this._syncCasesToJson();
            });
            return w;
        };

        // ── 延迟同步（首次渲染后）────────────────────────────────
        nodeType.prototype._doSync = function () {
            setTimeout(() => {
                try { this._syncIO(this._getCount()); }
                catch (e) { console.warn("AnyInputSwitch sync error:", e); }
            }, 0);
        };

        // ── 节点创建 ────────────────────────────────────────────
        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origCreated?.apply(this, arguments);

            // item_count callback
            const countWidget = this.widgets?.find(w => w.name === "item_count");
            if (countWidget) {
                const origCallback = countWidget.callback;
                countWidget.callback = (value, ...args) => {
                    if (origCallback) origCallback.call(countWidget, value, ...args);
                    this._syncIO(this._getCount());
                };
            }

            this._doSync();
        };

        // ── 工作流加载 ──────────────────────────────────────────
        const origConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            origConfigure?.apply(this, arguments);
            // __case_json 已被 origConfigure 还原，
            // _syncIO 内部会调用 _syncCasesFromJson 恢复各 case widget 值
            this._doSync();
        };

        nodeType.prototype._getCount = function () {
            const w = this.widgets?.find(w => w.name === "item_count");
            return Math.max(1, Math.min(MAX_ITEMS, parseInt(w?.value) || 1));
        };

        // ── 核心同步 ────────────────────────────────────────────
        nodeType.prototype._syncIO = function (count) {
            if (count == null) count = this._getCount();
            count = Math.max(1, Math.min(MAX_ITEMS, count));

            // ===== case_N widget：添加/删除（不碰 DOM）=====
            const existing = new Set();
            for (const w of (this.widgets || [])) {
                if (/^case_\d+$/.test(w.name)) {
                    existing.add(parseInt(w.name.split("_")[1]));
                }
            }

            // 删除多余的（count+1..MAX）
            for (let num = MAX_ITEMS; num > count; num--) {
                if (existing.has(num)) {
                    const idx = this.widgets.findIndex(w => w.name === `case_${num}`);
                    if (idx >= 0) {
                        this.widgets.splice(idx, 1);
                    }
                }
            }

            // 添加缺少的（1..count）
            for (let num = 1; num <= count; num++) {
                if (!existing.has(num)) {
                    this._addCaseWidget(num);
                }
            }

            // 从 __case_json 恢复 widget 值（工作流加载时 json 已还原）
            this._syncCasesFromJson();

            // 同步 case 值到 JSON
            this._syncCasesToJson();

            // ===== 隐藏 __case_json widget =====
            const jsonW = this.widgets?.find(w => w.name === "__case_json");
            if (jsonW) {
                jsonW.type = "hidden";
            }

            // ===== input_N slot =====
            for (let n = 1; n <= count; n++) {
                const name = `input_${n}`;
                if (!(this.inputs || []).find(s => s.name === name)) {
                    this.addInput(name, "*");
                }
            }
            for (let n = MAX_ITEMS; n > count; n--) {
                const name = `input_${n}`;
                const idx = (this.inputs || []).findIndex(s => s.name === name);
                if (idx >= 0 && this.inputs[idx].link == null) {
                    this.removeInput(idx);
                }
            }

            // ===== input_default 最后 =====
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
