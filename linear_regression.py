import matplotlib.pyplot as plt
import numpy as np
from sklearn import datasets, linear_model
from sklearn.metrics import mean_squared_error, r2_score

# using: https://scikit-learn.org/stable/auto_examples/linear_model/plot_ols.html


def splitter(values):
    # generate a vector, split into n chunks, fill in [values] for each
    # generates stepwise array -> "a team split, or t2 xp changed"
    vec = np.zeros(365)
    n = len(values) - 1  # must be n-1, fencepost problem
    ind = np.random.choice(range(vec.shape[0]), size=(n,), replace=False)
    ind = np.sort(ind)
    print(ind)

    # fill first chunk
    vec[: ind[0]] = values[0]

    # fill middle chunks
    if n >= 2:
        for i in range(0, n - 1):
            vec[ind[i] : ind[i + 1]] = values[i]

    # fill end chunk
    vec[ind[-1] :] = values[-1]
    print(vec)
    return vec


def increment_splitter(values, base, avg=False):
    # generate a vector, split into n chunks, fill in [values] for each
    # generates stepwise array -> "a team split, or t2 xp changed"
    # BUT this assumes we have num_t2s of equal days xp. generates a "number of t2s array" first
    # if one leaves, lose that much xp from the team (base + days in)
    # if avg=True, give me the per T2 xp
    count = splitter(values)
    num_t2s = values[0]
    increment_count = np.zeros(count.shape)
    increment_count[0] = base * num_t2s
    for i in range(1, len(count)):
        if count[i] >= count[i - 1]:
            increment_count[i] = increment_count[i - 1] + count[i]
        else:
            increment_count[i] = increment_count[i - 1] + count[i] - base - i

    if avg == True:
        increment_count = increment_count / count
    print(increment_count)
    return increment_count


## ticket count (random, increasing linear function)
days = np.arange(365)
delta = np.random.uniform(0.85, 1.15, size=(365,))  # vary by 30%
ticket_count = (2 * days + 1000) * delta

## escalation count (random subset of tickets)
delta = np.random.uniform(0.05, 0.15, size=(365,))  # 5-15% escalate
escalation_count = ticket_count * delta

# inputs:
# num tickets, num escalations, num teams,

print("splitter test")
splitter([1, 2, 3])
splitter([7, 2, 12, 15])

print("increment splitter test")
increment_splitter([2, 3, 2], 200)
increment_splitter([2, 3, 2], 200, avg=True)

print("Cloud time")
cloud_tickets = ticket_count
cloud_escalations = escalation_count
cloud_teams = splitter([2, 3])
cloud_age = increment_splitter([2, 3, 2], 130)

cloud_data = np.array(
    [cloud_tickets, cloud_escalations, cloud_teams, cloud_age]
)  # placeholder, not shaped correctly

# Split the data into training/testing sets
cloud_train_x = cloud_tickets[:72]
cloud_test_x = cloud_tickets[72:]

# Split the targets into training/testing sets
cloud_train_y = cloud_escalations[:72]
cloud_test_y = cloud_tickets[72:]

# Create linear regression object
regr = linear_model.LinearRegression()

# Train the model using the training sets
regr.fit(
    cloud_train_x.reshape(-1, 1), cloud_train_y.reshape(-1, 1)
)  # -1, 1 because it's single-dimension (arbitrary)

# Make predictions using the testing set
cloud_pred_y = regr.predict(cloud_test_x.reshape(-1, 1))

## these don't prove much, just an example.
# The coefficients
print("Coefficients: \n", regr.coef_)
# The mean squared error
print("Mean squared error: %.2f" % mean_squared_error(cloud_test_y, cloud_pred_y))
# The coefficient of determination: 1 is perfect prediction
print("Coefficient of determination: %.2f" % r2_score(cloud_test_y, cloud_pred_y))

# Plot outputs
plt.scatter(cloud_test_x, cloud_test_y.reshape(-1, 1), color="black")
plt.plot(cloud_test_x, cloud_pred_y.reshape(-1, 1), color="blue", linewidth=3)

plt.xticks(())
plt.yticks(())

plt.show()
