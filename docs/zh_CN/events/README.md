# 第七章：事件系统 (Events)

rhosocial-activerecord 的事件系统是实现业务逻辑解耦的关键机制。通过监听生命周期事件，你可以在不修改模型核心逻辑的情况下，添加诸如日志记录、数据校验、关联更新等功能。

## 目录

*   [生命周期事件 (Lifecycle Events)](lifecycle.md): 详解所有可用的钩子及其用法。

## 核心概念

*   **ModelEvent**: 枚举类型，定义了所有支持的事件点。
*   **Observer Pattern**: 基于观察者模式，支持多个监听器。
*   **Mixin Friendly**: 设计上鼓励通过 Mixin 组合行为。
