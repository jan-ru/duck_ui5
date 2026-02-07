let
    Source = stg_Combined,
    
    // =====================================================
    // 1. Keep only fact table columns (FKs + measures)
    // =====================================================
    FactColumns = Table.SelectColumns(Source, {
        // Foreign Keys
        "CodeGrootboekrekening",     // FK to dim_Account
        "LastDate",                   // FK to dim_Date
        "JaarPeriode",               // Period identifier
        "NaamAdministratie",        // FK to dim_Administratie

        // Degenerate dimensions (no separate dim table)
        "CodeRelatiekostenplaats",
        "NaamRelatiekostenplaats",
        
        // For filtering (needed for Profit calculation)
        "Code0",
        "Code1",
        
        // Measure
        "Value"
    }),
    
    // =====================================================
    // 2. Add DisplayValue (sign-corrected for reporting)
    // =====================================================
    // Need Categorie1 logic here for sign correction
    AddDisplayValue = Table.AddColumn(
        FactColumns,
        "DisplayValue",
        each 
            let
                cat1 = 
                    if List.Contains({"000","010","020","030","040","050"}, [Code1]) then "Activa"
                    else if List.Contains({"060","065","070","080"}, [Code1]) then "Passiva"
                    else if List.Contains({"500","510"}, [Code1]) then "Gross Margin"
                    else if List.Contains({"520","530","540","550"}, [Code1]) then "Expenses"
                    else null
            in
                if cat1 = "Activa" then [Value]
                else if cat1 = "Passiva" or cat1 = "Expenses" or cat1 = "Gross Margin" 
                    then [Value] * -1
                else null,
        type number
    ),
    
    // =====================================================
    // 3. Calculate Profit rows (for "Winst lopend boekjaar")
    // =====================================================
    BalanceOnly = Table.SelectRows(FactColumns, each [Code0] = "BAS"),
    
    ProfitPerPeriod = Table.Group(
        BalanceOnly,
        {"JaarPeriode", "LastDate", "NaamAdministratie"},
        {{"Profit", each List.Sum([Value]), type number}}
    ),
    
    ProfitRows = Table.AddColumn(
        ProfitPerPeriod,
        "Record",
        each [
            CodeGrootboekrekening = "9999",  // Synthetic account for profit
            Code0 = "BAS",
            Code1 = "060",
            CodeRelatiekostenplaats = null,
            NaamRelatiekostenplaats = null,
            Value = [Profit] * -1,
            DisplayValue = [Profit]
        ]
    ),
    
    ProfitExpanded = Table.ExpandRecordColumn(
        ProfitRows,
        "Record",
        {"CodeGrootboekrekening", "Code0", "Code1", "CodeRelatiekostenplaats", 
         "NaamRelatiekostenplaats", "Value", "DisplayValue"}
    ),
    
    // =====================================================
    // 4. Combine base rows + profit rows
    // =====================================================
    CombinedFact = Table.Combine({AddDisplayValue, ProfitExpanded}),
    
    // =====================================================
    // 5. Remove helper columns not needed downstream
    // =====================================================
    Final = Table.RemoveColumns(CombinedFact, {"Code0", "Code1"}),
    
    // =====================================================
    // 6. Set types
    // =====================================================
    Typed = Table.TransformColumnTypes(Final, {
        {"Value", type number}, 
        {"DisplayValue", type number},
        {"LastDate", type date}
    }),
    #"Filtered Rows" = Table.SelectRows(Typed, each true)
in
    #"Filtered Rows"