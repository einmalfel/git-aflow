from gitaflow.common import say, default_sources, check_iteration, \
    complete_branch_name
from gitaflow.topic import TopicMerge


NAME_WIDTH = 20
TERM_WIDTH = 80


def list_(sources, all_, filters):
    # prepare sources
    if all_:
        sources = ['master', 'staging', 'develop']
    if not sources:
        sources = default_sources()
    ci = check_iteration()

    for s in sources:
        s = complete_branch_name(s, ci)
        listed = []
        say((s[:NAME_WIDTH]).ljust(NAME_WIDTH, '-') +
            'Type |Ver| Description'.ljust(TERM_WIDTH - NAME_WIDTH, '-'))
        for m in reversed(TopicMerge.get_effective_merges_in(s)):
            if m.rev.topic not in listed and (not filters or m.type in filters):
                listed.append(m.rev.topic)
                output = '{:<{}} {} |{:^3}| {}'.format(
                    m.rev.topic.name[:NAME_WIDTH],
                    NAME_WIDTH,
                    m.type,
                    m.rev.version,
                    m.description if m.description else 'N/A')
                if len(output) > TERM_WIDTH:
                    output = output[:TERM_WIDTH - 3] + '...'
                say(output)
