import smartpy as sp

# A contract that takes tez deposits and pays interest. The deposited funds cannot leave
# the contract, but the administrator can delegate them for baking.

# The duration time set is in days
class PiggyBank(sp.Contract):
    def __init__(self, admin, initialRate, initialDuration):
        self.init(
            admin       = admin
          , collateral  = sp.mutez(0)
          , ledger      = {}
          , rate        = initialRate
          , duration    = initialDuration)

        self.add_flag("no-initial-cast")

    # Admin-only. Delegate the contract's balance.
    @sp.entry_point
    def delegate(self, baker):
        sp.verify(sp.sender == self.data.admin)
        sp.verify(sp.amount == sp.mutez(0))
        sp.set_delegate(baker)

    # Admin-only. Provide tez as collateral for interest to be paid.
    @sp.entry_point
    def collateralize(self, amount):
        sp.verify(sp.sender == self.data.admin)
        self.data.collateral += amount

    # Admin-only. Withdraw collateral.
    @sp.entry_point
    def uncollateralize(self, amount):
        sp.verify(sp.sender == self.data.admin)
        self.data.collateral -= amount
        sp.verify(self.data.collateral >= sp.mutez(0))

    # Admin-only. Set the current offer: interest rate (in basis points) and duration.
    @sp.entry_point
    def setOffer(self, rate, duration):
        sp.verify(sp.sender == self.data.admin)
        self.data.rate = rate
        self.data.duration = duration

    # Deposit tez. The current offer has to be repeated in the parametetrs.
    @sp.entry_point
    def deposit(self, rate, duration):
        sp.verify(self.data.rate     >= rate)
        sp.verify(self.data.duration <= duration)
        sp.verify(~ self.data.ledger.contains(sp.sender))

        # Compute interest to be paid.
        interest = sp.split_tokens(sp.amount, self.data.rate, 10000)
        self.data.collateral -= interest

        # Abort if calloteral is insuffiecent to pay interest.
        sp.verify(self.data.collateral >= sp.mutez(0))

        # Record the payment to be made.
        self.data.ledger[sp.sender] = sp.record(
              amount = sp.amount + interest
            , due    = sp.now.add_seconds(self.data.duration * 24 * 3600))

    # Withdraw tez at mutarity.
    @sp.entry_point
    def withdraw(self):
        entry = self.data.ledger[sp.sender]
        sp.verify(sp.now >= entry.due)
        sp.send(sp.sender,entry.amount)
        del self.data.ledger[sp.sender]

# Tests
@sp.add_test(name = "Saving")
def test():
    voting_powers = {
        sp.key_hash("tz1YB12JHVHw9GbN66wyfakGYgdTBvokmXQk"): 0,
    }
    scenario = sp.test_scenario()
    scenario.h1("Piggy Bank")

    admin = sp.test_account("Admin")

    c = PiggyBank(admin.address, 600, 30)

    scenario += c
    c.delegate(sp.some(sp.key_hash("tz1YB12JHVHw9GbN66wyfakGYgdTBvokmXQk"))).run(sender = admin, voting_powers = voting_powers)
    scenario.verify_equal(c.baker, sp.some(sp.key_hash("tz1YB12JHVHw9GbN66wyfakGYgdTBvokmXQk")))
    c.delegate(sp.none).run(sender = admin)
    scenario.verify_equal(c.baker, sp.none)

sp.add_compilation_target("piggyswap", PiggyBank(sp.test_account("admin").address, 700, 365))
