# DECISION-CONTROL-FOR-TRAFFIC-SIGNAL-
## Problem Statement 
We are examining traffic lights that are not adjusting per the movement of traffic. We approximate the intersection by modeling it with Markov Decision Process (MDP) and by a Poisson distribution to deal with uncertainty in the arrival of cars at the intersection. This allows us to create a system that is able to make decisions on-the-fly. We hope to identify optimum signal timing such that to reduce waiting time of drivers, indicating that a probabilistic approach is superior to fixed-schedule controllers.

## Random variables:
- **Arrivals in time interval**: Number of vehicles arriving at the cross
roads in one interval ∆t is random. We denote this arrival count by
n.
- **Arrival rate λ**: The arrival rate is also treated as uncertain as it can
fluctuate around accordingly with time.
- **Input flow qin(k)**: Since arrivals are random, the input flow becomes
random at each time step k.
- **Output flow qout(k)**: The output flow is also uncertain because it
depends on the signal u(k) (green or red) and the current queue.
- **Congestion state**: Each movement can be placed into one of two
states using a queue threshold: if queue > threshold it is congested,
otherwise it is non-congested.
- **State transitions**: Because arrivals and departures change the queue,
the congestion/non-congestion state can change over time, so we can
model this using transition probabilities between states.

## Members
- Hiya Soni  
- Jay Daftari
- Swayam Prajapati 
- Arya Patel 
- Ahladita Chaudary
