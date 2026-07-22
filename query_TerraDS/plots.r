library(ggplot2)
library(scales)

# Resource et repository
data <- read.csv("resource_distribution.csv")
plot1 <- ggplot(data, aes(x = resource_count, y = repository_count)) +
  geom_bar(stat = "identity", fill = "steelblue") +
  scale_x_continuous(limits = c(0, 1000)) +
  scale_y_continuous(
    trans = pseudo_log_trans(base = 10),
    labels = comma
  ) +
  labs(
    title = "Distribution of resources per repository",
    x = "Resource count",
    y = "Repository count"
  ) 
ggsave("resource_distribution.pdf", plot = plot1, width = 7, height = 4, units = "in")

# Resource et module
data <- read.csv("module_resource_distribution.csv")
plot2 <- ggplot(data, aes(x = resource_count, y = module_count)) +
  geom_bar(stat = "identity", fill = "steelblue") +
  scale_x_continuous(limits = c(0, 300)) +
  scale_y_continuous(
    trans = pseudo_log_trans(base = 10),
    labels = comma
  ) +
  labs(
    title = "Distribution of resources per module",
    x = "Resource count",
    y = "Module count"
  ) 

ggsave("module_resource_distribution.pdf", plot = plot2, width = 7, height = 4, units = "in")

