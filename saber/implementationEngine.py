from saber import metaLib as mtlib
from saber import metaData as mtd
import pandas as pd
import numpy as np

import datetime

mtw = mtlib.meta5_wrapper()

class execution:
    def __init__(self):
        self.mtw = mtw
        self.acc_pos = mtw.get_positions()

    def execution_check(self,new_pos,curr_pos,threshold = 0.1):
        if curr_pos ==0:
            return True
        elif abs((new_pos - curr_pos)/curr_pos)>=threshold:
            print(new_pos,curr_pos,abs((new_pos - curr_pos)/curr_pos))
            return True
        else:
            return False

    def get_total_posn_by_symbol(self,symbol):
        """
        Given an asset we calculate the total position in the book by volume * direction
        Note: This could possibly be in a
        """
        direction = self.acc_pos[symbol]['type']
        direction = [-1 if drtn == 1 else 1 for drtn in direction]
        volumes = self.acc_pos[symbol]['volume']
        total_posn = sum(x*y for x,y in zip(direction,volumes))
        return total_posn
    
    def get_trade_tickets_by_symbol(self,symbol):
        tickets = self.acc_pos[symbol]['ticket']
        return tickets
    
    def get_posn_by_symbol(self,symbol):
        direction = self.acc_pos[symbol]['type']
        direction = [-1 if drtn == 1 else 1 for drtn in direction]
        volumes = self.acc_pos[symbol]['volume']
        posns = [x*y for x,y in zip(direction,volumes)]
        return posns     
        

    def execute_trades(self,target_positions,exec_threshold = 0.1):
        acc_pos = self.acc_pos
        for sym in target_positions.keys():
            try:
                if sym in acc_pos.keys():
                    curr_dir = acc_pos[sym]['type']
                    if curr_dir ==0:
                        curr_dir = 1
                    elif curr_dir == 1:
                        curr_dir = -1
                    curr_pos = self.get_total_posn_by_symbol(sym)  #total pos
                    indiv_pos = self.get_posn_by_symbol(sym)
                    curr_pos_tickets = self.get_trade_tickets_by_symbol(sym)
                    
                    new_pos = target_positions[sym] - curr_pos
                    if new_pos ==0:
                        print(f"{sym} No change in position")
                        continue
                    elif new_pos*curr_pos <0:
                        # new signal changes direction of existing position, need to close out existing position
                        
                        if abs(new_pos) > abs(curr_pos):
                            
                            #Close our current position and trade new position if the size is bigger for the new position
                            if self.execution_check(new_pos,curr_pos,exec_threshold):
                                for tkt in curr_pos_tickets:
                                    self.mtw.close_position_by_ticket(tkt) #close current position first
                                new_pos = target_positions[sym]
                                # then execute new signal in opposite direction
                                exec_side = "BUY" if new_pos>0 else "SELL"
                                self.mtw.place_market_order(
                                    symbol=sym,
                                    side=exec_side,
                                    volume_lots=abs(new_pos)#,
                                    #sl = 3000.0,
                                    #tp = 5000.0
                                    )   
                                print(f"{sym}: Change of direction, closing out position {exec_side}{new_pos}")
                        else:
                            if self.execution_check(new_pos,curr_pos,exec_threshold):
                                
                                for i in range(len(curr_pos_tickets)):
                                    existing_volume = indiv_pos[i]
                                    tkt  = curr_pos_tickets[i]
                                    close_volume = min(abs(existing_volume),abs(new_pos))
                                    self.mtw.close_position_by_ticket(tkt,abs(close_volume))
                                    new_pos -= ((new_pos)/(abs(new_pos)))*close_volume
                                    print(f'{sym}: Reducing position {min(abs(existing_volume),abs(new_pos))}')



                    else:
                        print("Same direction")
                        #if abs()
                        if self.execution_check(new_pos,curr_pos,exec_threshold):
                            
                            exec_side = "BUY" if new_pos>0 else "SELL"
                            self.mtw.place_market_order(
                                symbol=sym,
                                side=exec_side,
                                volume_lots=abs(new_pos)#,
                                #sl = 3000.0,
                                #tp = 5000.0
                                )
                            print(f"{sym}: Change in position substantial, executing {exec_side}{new_pos}")
                        else:
                            print("Change in position too small, no action")
                        
                else:
                    print(f"{sym} No existing position, executing new position")
                    new_pos = target_positions[sym]
                    if self.execution_check(new_pos,0,exec_threshold): #Since no new position, curr_pos in execution check is equal to zero
                        exec_side = "BUY" if new_pos>0 else "SELL"
                        self.mtw.place_market_order(
                            symbol=sym,
                            side=exec_side,
                            volume_lots=abs(new_pos)#,
                            #sl = 3000.0,
                            #tp = 5000.0
                            )
            except Exception as e:
                print(f"{e} {sym} {new_pos}")
                pass

    