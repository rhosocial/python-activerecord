# 组件结构图

本文档提供了 rhosocial ActiveRecord 框架各核心组件的详细结构图。这些图表展示了每个组件的内部架构、类关系和交互方式。

## ActiveRecord Base 结构

```mermaid
flowchart TD
    %% 核心类
    AR["ActiveRecord"]:::core
    ARB["ActiveRecordBase"]:::core
    QM["QueryMixin"]:::core
    
    %% 接口
    MI["ModelInterface"]:::interface
    QI["QueryInterface"]:::interface
    UI["UpdateInterface"]:::interface
    
    %% 字段组件
    FD["字段定义"]:::field
    
    %% 查询组件
    AQ["ActiveQuery"]:::query
    
    %% 关系组件
    RL["关系层"]:::relation
    
    %% 后端组件
    BA["后端抽象"]:::backend
    
    %% 继承和实现
    ARB -->|"继承"| MI
    QM -->|"继承"| QI
    AR -->|"继承"| ARB
    AR -->|"继承"| QM
    AR -->|"实现"| UI
    
    %% 使用和组合
    AR -->|"使用"| FD
    AR -->|"创建"| AQ
    AR -->|"管理"| RL
    AR -->|"通过连接"| BA
    
    %% 生命周期和事件
    AR -->|"生命周期事件"| AR
    
    %% 样式
    classDef core fill:#F9E79F,stroke:#B9770E,stroke-width:2px;
    classDef interface fill:#FDEBD0,stroke:#CA6F1E,stroke-width:2px;
    classDef field fill:#AED6F1,stroke:#2471A3,stroke-width:2px;
    classDef query fill:#A9DFBF,stroke:#196F3D,stroke-width:2px;
    classDef relation fill:#D2B4DE,stroke:#6C3483,stroke-width:2px;
    classDef backend fill:#F5B7B1,stroke:#C0392B,stroke-width:2px;
```

## 字段定义结构

```mermaid
flowchart TD
    %% 核心字段组件
    FD["字段定义"]:::field
    
    %% 字段类型
    IPK["整数主键"]:::field
    UPK["UUID主键"]:::field
    TS["时间戳字段"]:::field
    SD["软删除"]:::field
    VF["版本字段"]:::field
    CF["自定义字段"]:::field
    
    %% 验证
    PD["Pydantic"]:::external
    
    %% 关系
    FD -->|"包含"| IPK
    FD -->|"包含"| UPK
    FD -->|"包含"| TS
    FD -->|"包含"| SD
    FD -->|"包含"| VF
    FD -->|"包含"| CF
    FD -->|"通过验证"| PD
    
    %% 字段行为
    IPK -->|"自动递增"| IPK
    UPK -->|"生成"| UPK
    TS -->|"自动更新"| TS
    SD -->|"标记删除"| SD
    VF -->|"跟踪变更"| VF
    
    %% 样式
    classDef field fill:#AED6F1,stroke:#2471A3,stroke-width:2px;
    classDef external fill:#FAD7A0,stroke:#E67E22,stroke-width:2px;
```

## 查询构建器结构

```mermaid
flowchart TD
    %% 核心查询组件
    QB["查询构建器"]:::query
    AQ["ActiveQuery"]:::query
    BQ["BaseQuery"]:::query
    DQ["DictQuery"]:::query
    
    %% 查询功能
    EX["表达式"]:::query
    AG["聚合"]:::query
    JN["连接"]:::query
    RQ["范围查询"]:::query
    RLQ["关系查询"]:::query
    
    %% 后端集成
    BA["后端抽象"]:::backend
    SQL["SQL生成"]:::backend
    
    %% 继承和实现
    QB -->|"包含"| BQ
    BQ -->|"扩展为"| AQ
    BQ -->|"扩展为"| DQ
    
    %% 功能组合
    AQ -->|"使用"| EX
    AQ -->|"支持"| AG
    AQ -->|"执行"| JN
    AQ -->|"支持"| RQ
    AQ -->|"执行"| RLQ
    
    %% 后端执行
    AQ -->|"通过执行"| BA
    BA -->|"生成"| SQL
    
    %% 样式
    classDef query fill:#A9DFBF,stroke:#196F3D,stroke-width:2px;
    classDef backend fill:#F5B7B1,stroke:#C0392B,stroke-width:2px;
```

## 接口层结构

```mermaid
flowchart TD
    %% 核心接口组件
    IL["接口层"]:::interface
    MI["模型接口"]:::interface
    QI["查询接口"]:::interface
    UI["更新接口"]:::interface
    
    %% 实现类
    AR["ActiveRecord"]:::core
    AQ["ActiveQuery"]:::query
    
    %% 接口方法
    CRUD["CRUD操作"]:::method
    QM["查询方法"]:::method
    UM["更新方法"]:::method
    
    %% 关系
    IL -->|"定义"| MI
    IL -->|"定义"| QI
    IL -->|"定义"| UI
    
    MI -->|"由实现"| AR
    QI -->|"由实现"| AQ
    UI -->|"由实现"| AR
    
    MI -->|"提供"| CRUD
    QI -->|"提供"| QM
    UI -->|"提供"| UM
    
    %% 样式
    classDef interface fill:#FDEBD0,stroke:#CA6F1E,stroke-width:2px;
    classDef core fill:#F9E79F,stroke:#B9770E,stroke-width:2px;
    classDef query fill:#A9DFBF,stroke:#196F3D,stroke-width:2px;
    classDef method fill:#D5F5E3,stroke:#1E8449,stroke-width:1px;
```

## 关系层结构

```mermaid
flowchart TD
    %% 核心关系组件
    RL["关系层"]:::relation
    RB["关系基类"]:::relation
    RC["关系缓存"]:::relation
    RD["关系描述符"]:::relation
    RI["关系接口"]:::relation
    
    %% 关系类型
    BT["从属于"]:::relation
    HO["拥有一个"]:::relation
    HM["拥有多个"]:::relation
    MM["多对多"]:::relation
    PR["多态关系"]:::relation
    SR["自引用"]:::relation
    
    %% 加载策略
    LL["懒加载"]:::strategy
    EL["急加载"]:::strategy
    PL["预加载"]:::strategy
    
    %% 关系
    RL -->|"定义"| RB
    RL -->|"利用"| RC
    RL -->|"通过实现"| RD
    RL -->|"指定"| RI
    
    RB -->|"扩展为"| BT
    RB -->|"扩展为"| HO
    RB -->|"扩展为"| HM
    RB -->|"扩展为"| MM
    RB -->|"扩展为"| PR
    RB -->|"扩展为"| SR
    
    RL -->|"支持"| LL
    RL -->|"支持"| EL
    RL -->|"支持"| PL
    
    %% 样式
    classDef relation fill:#D2B4DE,stroke:#6C3483,stroke-width:2px;
    classDef strategy fill:#D6EAF8,stroke:#2E86C1,stroke-width:1px;
```

这些图表提供了 rhosocial ActiveRecord 框架各核心组件内部结构和关系的可视化表示。它们展示了不同部分如何交互并协同工作，以提供完整的 ORM 功能。