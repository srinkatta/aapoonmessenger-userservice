class MasterSlaveRouter:
    def db_for_read(self, model, **hints):
        """
        Reads go to a slave1 replica of master db
        """
        return "slave1"

    def db_for_write(self, model, **hints):
        """
        Writes always go to default(primary).
        """
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """
        Relations between objects are allowed if both objects are
        in the primary/replica pool.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True
