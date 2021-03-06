if __name__ == "__main__":

    import sys

    from os.path import abspath, dirname, join

    path = abspath(join(dirname(__file__), '..'))
    sys.path.insert(1, path)

    from jinja2 import Template

    deployment_id, deployment_group = sys.argv[1:]

    domains = {
        'production': 'budget.e-vz.com',
    }

    nginx_template_path = '/home/evz/budget-{}/configs/nginx_template.conf'.format(
        deployment_id)
    nginx_outpath = '/etc/nginx/conf.d/budget.conf'
    supervisor_template_path = '/home/evz/budget-{}/configs/supervisor_template.conf'.format(
        deployment_id)
    supervisor_outpath = '/etc/supervisor/conf.d/budget.conf'
    alembic_template_path = '/home/evz/budget-{}/configs/alembic_template.ini'.format(
        deployment_id)
    alembic_outpath = '/home/evz/budget-{}/alembic.ini'.format(deployment_id)

    with open(nginx_template_path) as f:
        nginx_conf = Template(f.read())
        context = {
            'deployment_id': deployment_id,
            'domain': domains[deployment_group]
        }
        nginx_rendered = nginx_conf.render(context)

    with open(supervisor_template_path) as f:
        supervisor_conf = Template(f.read())
        supervisor_rendered = supervisor_conf.render(
            {'deployment_id': deployment_id})

    with open(alembic_template_path) as f:
        alembic_conf = Template(f.read())
        alembic_rendered = alembic_conf.render(
            {'deployment_id': deployment_id})

    with open(nginx_outpath, 'w') as out:
        out.write(nginx_rendered)

    with open(supervisor_outpath, 'w') as out:
        out.write(supervisor_rendered)

    with open(alembic_outpath, 'w') as out:
        out.write(alembic_rendered)
