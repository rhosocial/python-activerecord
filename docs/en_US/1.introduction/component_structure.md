# Component Structure Diagrams

This document provides detailed structure diagrams for each core component of the rhosocial ActiveRecord framework. These diagrams illustrate the internal architecture, class relationships, and interactions within each component.

## ActiveRecord Base Structure

```mermaid
flowchart TD
    %% Core Classes
    AR["ActiveRecord"]:::core
    ARB["ActiveRecordBase"]:::core
    QM["QueryMixin"]:::core
    
    %% Interfaces
    MI["ModelInterface"]:::interface
    QI["QueryInterface"]:::interface
    UI["UpdateInterface"]:::interface
    
    %% Field Components
    FD["Field Definitions"]:::field
    
    %% Query Components
    AQ["ActiveQuery"]:::query
    
    %% Relation Components
    RL["Relation Layer"]:::relation
    
    %% Backend Components
    BA["Backend Abstraction"]:::backend
    
    %% Inheritance and Implementation
    ARB -->|"inherits"| MI
    QM -->|"inherits"| QI
    AR -->|"inherits"| ARB
    AR -->|"inherits"| QM
    AR -->|"implements"| UI
    
    %% Usage and Composition
    AR -->|"uses"| FD
    AR -->|"creates"| AQ
    AR -->|"manages"| RL
    AR -->|"connects via"| BA
    
    %% Lifecycle and Events
    AR -->|"lifecycle events"| AR
    
    %% Styles
    classDef core fill:#F9E79F,stroke:#B9770E,stroke-width:2px;
    classDef interface fill:#FDEBD0,stroke:#CA6F1E,stroke-width:2px;
    classDef field fill:#AED6F1,stroke:#2471A3,stroke-width:2px;
    classDef query fill:#A9DFBF,stroke:#196F3D,stroke-width:2px;
    classDef relation fill:#D2B4DE,stroke:#6C3483,stroke-width:2px;
    classDef backend fill:#F5B7B1,stroke:#C0392B,stroke-width:2px;
```

## Field Definitions Structure

```mermaid
flowchart TD
    %% Core Field Components
    FD["Field Definitions"]:::field
    
    %% Field Types
    IPK["IntegerPK"]:::field
    UPK["UuidPK"]:::field
    TS["Timestamp Fields"]:::field
    SD["SoftDelete"]:::field
    VF["Version Field"]:::field
    CF["Custom Fields"]:::field
    
    %% Validation
    PD["Pydantic"]:::external
    
    %% Relationships
    FD -->|"includes"| IPK
    FD -->|"includes"| UPK
    FD -->|"includes"| TS
    FD -->|"includes"| SD
    FD -->|"includes"| VF
    FD -->|"includes"| CF
    FD -->|"validates with"| PD
    
    %% Field Behaviors
    IPK -->|"auto increment"| IPK
    UPK -->|"generates"| UPK
    TS -->|"auto update"| TS
    SD -->|"marks deleted"| SD
    VF -->|"tracks changes"| VF
    
    %% Styles
    classDef field fill:#AED6F1,stroke:#2471A3,stroke-width:2px;
    classDef external fill:#FAD7A0,stroke:#E67E22,stroke-width:2px;
```

## Query Builder Structure

```mermaid
flowchart TD
    %% Core Query Components
    QB["Query Builder"]:::query
    AQ["ActiveQuery"]:::query
    BQ["BaseQuery"]:::query
    DQ["DictQuery"]:::query
    
    %% Query Features
    EX["Expressions"]:::query
    AG["Aggregations"]:::query
    JN["Joins"]:::query
    RQ["Range Queries"]:::query
    RLQ["Relational Queries"]:::query
    
    %% Backend Integration
    BA["Backend Abstraction"]:::backend
    SQL["SQL Generation"]:::backend
    
    %% Inheritance and Implementation
    QB -->|"contains"| BQ
    BQ -->|"extended by"| AQ
    BQ -->|"extended by"| DQ
    
    %% Feature Composition
    AQ -->|"uses"| EX
    AQ -->|"supports"| AG
    AQ -->|"performs"| JN
    AQ -->|"supports"| RQ
    AQ -->|"executes"| RLQ
    
    %% Backend Execution
    AQ -->|"executes through"| BA
    BA -->|"generates"| SQL
    
    %% Styles
    classDef query fill:#A9DFBF,stroke:#196F3D,stroke-width:2px;
    classDef backend fill:#F5B7B1,stroke:#C0392B,stroke-width:2px;
```

## Interface Layer Structure

```mermaid
flowchart TD
    %% Core Interface Components
    IL["Interface Layer"]:::interface
    MI["ModelInterface"]:::interface
    QI["QueryInterface"]:::interface
    UI["UpdateInterface"]:::interface
    
    %% Implementation Classes
    AR["ActiveRecord"]:::core
    AQ["ActiveQuery"]:::query
    
    %% Interface Methods
    CRUD["CRUD Operations"]:::method
    QM["Query Methods"]:::method
    UM["Update Methods"]:::method
    
    %% Relationships
    IL -->|"defines"| MI
    IL -->|"defines"| QI
    IL -->|"defines"| UI
    
    MI -->|"implemented by"| AR
    QI -->|"implemented by"| AQ
    UI -->|"implemented by"| AR
    
    MI -->|"provides"| CRUD
    QI -->|"provides"| QM
    UI -->|"provides"| UM
    
    %% Styles
    classDef interface fill:#FDEBD0,stroke:#CA6F1E,stroke-width:2px;
    classDef core fill:#F9E79F,stroke:#B9770E,stroke-width:2px;
    classDef query fill:#A9DFBF,stroke:#196F3D,stroke-width:2px;
    classDef method fill:#D5F5E3,stroke:#1E8449,stroke-width:1px;
```

## Relation Layer Structure

```mermaid
flowchart TD
    %% Core Relation Components
    RL["Relation Layer"]:::relation
    RB["Relation Base"]:::relation
    RC["Relation Cache"]:::relation
    RD["Relation Descriptors"]:::relation
    RI["Relation Interfaces"]:::relation
    
    %% Relation Types
    BT["BelongsTo"]:::relation
    HO["HasOne"]:::relation
    HM["HasMany"]:::relation
    MM["ManyToMany"]:::relation
    PR["Polymorphic Relations"]:::relation
    SR["Self-Referential"]:::relation
    
    %% Loading Strategies
    LL["Lazy Loading"]:::strategy
    EL["Eager Loading"]:::strategy
    PL["Preload"]:::strategy
    
    %% Relationships
    RL -->|"defines"| RB
    RL -->|"utilizes"| RC
    RL -->|"implements via"| RD
    RL -->|"specifies"| RI
    
    RB -->|"extends to"| BT
    RB -->|"extends to"| HO
    RB -->|"extends to"| HM
    RB -->|"extends to"| MM
    RB -->|"extends to"| PR
    RB -->|"extends to"| SR
    
    RL -->|"supports"| LL
    RL -->|"supports"| EL
    RL -->|"supports"| PL
    
    %% Styles
    classDef relation fill:#D2B4DE,stroke:#6C3483,stroke-width:2px;
    classDef strategy fill:#D6EAF8,stroke:#2E86C1,stroke-width:1px;
```

These diagrams provide a visual representation of the internal structure and relationships within each core component of the rhosocial ActiveRecord framework. They illustrate how the different parts interact and work together to provide the complete ORM functionality.