Protection Circuit Module (PCB) for 7.4V Li-PO & Li-ion 18650 / 18500 Battery Packs (11A Limit)
=============================================================================================== 

http://www.amazon.com/Protection-Circuit-Module-Li-ion-Battery/dp/B00N48RCS8

Features and Benefits:
    
    Protection Circuit Board for 2S Li-ion and Li-polymer battery pack
    Designed for 2S Li-ion or Li-Polymer battery
    Prevents 2S Li-ion or Li-polymer battery from over-charging, over-discharging and from discharging current more than 8A (11A cut-off).
    Fully Compatible with both Li-ion and Li-Polymer cells

Specifications:

    Normal Temperature: 25℃
    Over charge detection voltage: 4.25±0.025V
    Over charge detection delay time: 1.0±0.3s
    Over charge release voltage: 4.05±0.05V
    Over discharge protection voltage: 2.4±0.06V = 4.8
    Over discharge detection delay time: 128±39ms
    Over discharge release voltage: 3.0±0.075V
    Rated operational current: ≤5A
    Over current detection current: 11±3A
    Release condition: Cut load 
    Detection delay time: 8-16ms
    Detection condition: Exterior short circuit
    Protection: Have
    Release condition: Cut short circuit
    Main loop electrify resistance: Rss≤50mΩ
    Current consume in normal operation: 8μA Max
    Dimensions: 38 x 8 x 3.5 mm

I thought this board was DOA because I wired it up to a 18650 cell holder, popped in a couple of fully charged cells, and got no output from it. It somehow occurred to me to apply a charge voltage to the output of the pack (P- and P+) and voila the output latched on. So if this board detects an over-discharged cell, it will latch off until a charger is connected to the pack. This is OK if you want to solder it into your pack, but for swapping in cells, watch out. I'm working around this by installing a momentary switch between B- and P-. Shorting these will create the cell voltage at the P+, P- terminals and will latch the circuit on.

As far as I can tell, the controlling IC is a Ricoh R5460N208AF. It does not balance cells during charging, it shuts off all the current if the voltage of either cell exceeds a limit (4.25). It also shuts off the current if the voltage of either cell drops below the limit (2.40). With a set of really unbalanced cells, I think you can quickly get into trouble.

The B- terminal goes to cell 1 -, B1 goes to cell 1 + / cell 2 -, and B+ goes to cell 2 +. So B- = 0.0v, B1 = 3.7v, B+ = 7.4v. P- is pack out - (0v) and P+ is pack out + (7.4v). The pad under P- has no connection and the T pad has no connection.
